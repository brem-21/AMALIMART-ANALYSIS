import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import apriori, association_rules

from fastapi import FastAPI, Query
from typing import List
import uvicorn

app = FastAPI()

products = pd.read_excel(
    "./data/realistic_ecommerce_data_updated.xlsx", sheet_name="products"
)
cart_items = pd.read_excel(
    "./data/realistic_ecommerce_data_updated.xlsx", sheet_name="cart_items"
)

products = products[products["status"] == "ACTIVE"].copy()
products["text"] = (
    products["name"].fillna("") + " " + products["description"].fillna("")
)

cart_items = cart_items[cart_items["product_id"].isin(products["id"])]
cart_items = cart_items.merge(
    products[["id", "name"]], left_on="product_id", right_on="id"
)

transactions = cart_items.groupby("cart_id")["name"].apply(list).tolist()

te = TransactionEncoder()
te_array = te.fit(transactions).transform(transactions)
df_trans = pd.DataFrame(te_array, columns=te.columns_)

frequent_itemsets = apriori(
    df_trans.astype("bool"), min_support=0.01, use_colnames=True
)
rules_df = association_rules(frequent_itemsets, metric="lift", min_threshold=0.5)
rules_df = rules_df[["antecedents", "consequents", "support", "confidence", "lift"]]


def market_based_recommend(cart_items, rules_df):
    recs = set()
    for item in cart_items:
        matched = rules_df[rules_df["antecedents"].apply(lambda x: item in x)]
        for conseq in matched["consequents"]:
            recs.update(conseq)
    return list(recs - set(cart_items))


tfidf = TfidfVectorizer(stop_words="english")
tfidf_matrix = tfidf.fit_transform(products["text"])
cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)
id_to_index = pd.Series(products.index, index=products["id"])


def get_similar_products(product_id, top_n=10):
    if product_id not in id_to_index:
        return []
    idx = id_to_index[product_id]
    if idx >= cosine_sim.shape[0]:
        return []
    sim_scores = list(enumerate(cosine_sim[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)[1 : top_n + 1]
    return products.iloc[[i[0] for i in sim_scores]]["name"].tolist()


def content_based_recommend(product_ids):
    recs = set()
    for pid in product_ids:
        recs.update(get_similar_products(pid))
    return list(recs)


user_item_matrix = (
    cart_items.groupby(["cart_id", "name"])["quantity"].sum().unstack().fillna(0)
)
item_user_matrix = user_item_matrix.T
item_sim = cosine_similarity(item_user_matrix)
item_sim_df = pd.DataFrame(
    item_sim, index=item_user_matrix.index, columns=item_user_matrix.index
)


def get_similar_items(item_name, top_n=10):
    if item_name not in item_sim_df.columns:
        return []
    return (
        item_sim_df[item_name]
        .sort_values(ascending=False)[1 : top_n + 1]
        .index.tolist()
    )


def collaborative_recommend(product_names):
    recs = set()
    for name in product_names:
        recs.update(get_similar_items(name))
    return list(recs)


# Map product name → product_id for join later
name_to_id = products.set_index("name")["id"].to_dict()


def hybrid_recommend(
    user_cart_ids,
    user_cart_names,
    weights={"market": 0.4, "content": 0.3, "collab": 0.3},
):
    score = defaultdict(float)
    sources = defaultdict(lambda: {"market": 0, "content": 0, "collab": 0})

    # Market-Based
    for item in market_based_recommend(user_cart_names, rules_df):
        score[item] += weights["market"]
        sources[item]["market"] = 1

    # Content-Based
    for item in content_based_recommend(user_cart_ids):
        score[item] += weights["content"]
        sources[item]["content"] = 1

    # Collaborative
    for item in collaborative_recommend(user_cart_names):
        score[item] += weights["collab"]
        sources[item]["collab"] = 1

    # Convert to product_id and attach metadata
    result = []
    top_n =10
    for name in sorted(score, key=score.get, reverse=True)[:top_n]:
        if name in name_to_id:
            pid = int(name_to_id[name])  # ensure it's a native int
            product_row = products[products["id"] == pid].iloc[0]

            result.append(
                {
                    "id": int(product_row["id"]),
                    "name": product_row["name"],
                    "description": product_row["description"],
                    "sku": product_row["sku"],
                    "price": (
                        float(product_row["price"])
                        if not pd.isna(product_row["price"])
                        else None
                    ),
                    "stock_quantity": (
                        int(product_row["stock_quantity"])
                        if not pd.isna(product_row["stock_quantity"])
                        else None
                    ),
                    "weight": (
                        float(product_row["weight"])
                        if not pd.isna(product_row["weight"])
                        else None
                    ),
                    "status": product_row["status"],
                    "vendor_id": (
                        int(product_row["vendor_id"])
                        if not pd.isna(product_row["vendor_id"])
                        else None
                    ),
                    "low_stock_threshold": (
                        int(product_row["low_stock_threshold"])
                        if not pd.isna(product_row["low_stock_threshold"])
                        else None
                    ),
                    "min_order_quantity": (
                        int(product_row["min_order_quantity"])
                        if not pd.isna(product_row["min_order_quantity"])
                        else None
                    ),
                    "average_rating": (
                        float(product_row["average_rating"])
                        if not pd.isna(product_row["average_rating"])
                        else None
                    ),
                    "thumbnail_url": product_row["thumbnail_url"],
                    "image_urls": (
                        product_row["image_urls"].split(",")
                        if pd.notna(product_row["image_urls"])
                        else []
                    ),
                    "is_active": bool(product_row["is_active"]),
                    "created_at": str(product_row["created_at"]),
                    "updated_at": str(product_row["updated_at"]),
                }
            )
    return result


@app.get("/recommendations")
def recommend(cart_ids: List[int] = Query(...)):
    cart_subset = cart_items[cart_items["cart_id"].isin(cart_ids)]
    user_cart_names = cart_subset["name"].tolist()
    user_cart_product_ids = cart_subset["product_id"].tolist()
    return hybrid_recommend(user_cart_product_ids, user_cart_names)


if __name__ == "__main__":
    uvicorn.run("hybrid_recommender:app", host="0.0.0.0", port=8000, reload=True)
