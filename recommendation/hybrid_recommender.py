import os
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import apriori, association_rules
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Query
from typing import List
import uvicorn
import pymssql
from dotenv import load_dotenv
import mysql.connector


# Load environment variables from .env
load_dotenv()
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("FRONTEND_URL", "").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Database connection
def get_connection():
    return mysql.connector.connect(
        host=os.getenv("SQL_SERVER_HOST"),
        user=os.getenv("SQL_SERVER_USER"),
        password=os.getenv("SQL_SERVER_PASSWORD"),
        database=os.getenv("SQL_SERVER_DATABASE"),
        port=3306
    )
# Load data from SQL Server
def load_data():
    conn = get_connection()
    products = pd.read_sql("SELECT * FROM products", conn)
    cart_items = pd.read_sql("SELECT * FROM cart_items", conn)
    conn.close()
    return products, cart_items
def market_based_recommend(cart_items, rules_df):
    if rules_df.empty or 'consequents' not in rules_df.columns:
        return []
    recs = set()
    for item in cart_items:
        matched = rules_df[rules_df["antecedents"].apply(lambda x: item in x)]
        for conseq in matched["consequents"]:
            recs.update(conseq)
    return list(recs - set(cart_items))

def get_similar_products(product_id, products, cosine_sim, id_to_index, top_n=10):
    if product_id not in id_to_index:
        return []
    idx = id_to_index[product_id]
    if idx >= cosine_sim.shape[0]:
        return []
    sim_scores = list(enumerate(cosine_sim[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)[1 : top_n + 1]
    return products.iloc[[i[0] for i in sim_scores]]["name"].tolist()

def content_based_recommend(product_ids, products, cosine_sim, id_to_index):
    recs = set()
    for pid in product_ids:
        recs.update(get_similar_products(pid, products, cosine_sim, id_to_index))
    return list(recs)

def get_similar_items(item_name, item_sim_df, top_n=10):
    if item_name not in item_sim_df.columns:
        return []
    return item_sim_df[item_name].sort_values(ascending=False)[1:top_n+1].index.tolist()

def collaborative_recommend(product_names, item_sim_df):
    recs = set()
    for name in product_names:
        recs.update(get_similar_items(name, item_sim_df))
    return list(recs)

@app.get("/")
def health_check():
    return {"status": "ok", "message": "Hybrid Recommender API is running"}

@app.get("/recommendations")
def recommend(cart_ids: List[int] = Query(...)):
    products, cart_items = load_data()
    products = products[products["status"] == "ACTIVE"].copy()
    products["text"] = products["name"].fillna("") + " " + products["description"].fillna("")
    cart_items = cart_items[cart_items["product_id"].isin(products["id"])]
    cart_items = cart_items.merge(products[["id", "name"]], left_on="product_id", right_on="id")
    
    # Build models with current data
    transactions = cart_items.groupby("cart_id")["name"].apply(list).tolist()
    te = TransactionEncoder()
    te_array = te.fit(transactions).transform(transactions)
    df_trans = pd.DataFrame(te_array, columns=te.columns_)
    
    frequent_itemsets = apriori(df_trans.astype("bool"), min_support=0.01, use_colnames=True)
    rules_df = association_rules(frequent_itemsets, metric="lift", min_threshold=0.5) if len(frequent_itemsets) > 0 else pd.DataFrame()
    
    tfidf = TfidfVectorizer(stop_words="english")
    tfidf_matrix = tfidf.fit_transform(products["text"])
    cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)
    id_to_index = {pid: idx for idx, pid in enumerate(products["id"])}
    
    user_item_matrix = cart_items.groupby(["cart_id", "name"])["quantity"].sum().unstack().fillna(0)
    item_user_matrix = user_item_matrix.T
    item_sim = cosine_similarity(item_user_matrix)
    item_sim_df = pd.DataFrame(item_sim, index=item_user_matrix.index, columns=item_user_matrix.index)
    
    user_cart_subset = cart_items[cart_items["cart_id"].isin(cart_ids)]
    user_cart_names = user_cart_subset["name"].tolist()
    user_cart_product_ids = user_cart_subset["product_id"].tolist()
    
    score = defaultdict(float)
    weights = {"market": 0.4, "content": 0.3, "collab": 0.3}
    
    try:
        for item in market_based_recommend(user_cart_names, rules_df):
            score[item] += weights["market"]
    except:
        pass
    try:
        for item in content_based_recommend(user_cart_product_ids, products, cosine_sim, id_to_index):
            score[item] += weights["content"]
    except:
        pass
    try:
        for item in collaborative_recommend(user_cart_names, item_sim_df):
            score[item] += weights["collab"]
    except:
        pass
    
    name_to_id = products.set_index("name")["id"].to_dict()
    result = []
    for name in sorted(score, key=score.get, reverse=True)[:10]:
        if name in name_to_id:
            pid = int(name_to_id[name])
            product_row = products[products["id"] == pid].iloc[0]
            result.append({
                "id": int(product_row["id"]),
                "name": product_row["name"],
                "description": product_row["description"],
                "sku": product_row["sku"],
                "price": float(product_row["price"]) if not pd.isna(product_row["price"]) else None,
                "stock_quantity": int(product_row["stock_quantity"]) if not pd.isna(product_row["stock_quantity"]) else None,
                "weight": float(product_row["weight"]) if not pd.isna(product_row["weight"]) else None,
                "status": product_row["status"],
                "vendor_id": int(product_row["vendor_id"]) if not pd.isna(product_row["vendor_id"]) else None,
                "low_stock_threshold": int(product_row["low_stock_threshold"]) if not pd.isna(product_row["low_stock_threshold"]) else None,
                "min_order_quantity": int(product_row["min_order_quantity"]) if not pd.isna(product_row["min_order_quantity"]) else None,
                "average_rating": float(product_row["average_rating"]) if not pd.isna(product_row["average_rating"]) else None,
                "thumbnail_url": product_row["thumbnail_url"],
                "image_urls": product_row["image_urls"].split(",") if pd.notna(product_row["image_urls"]) else [],
                "is_active": bool(product_row["is_active"]),
                "created_at": str(product_row["created_at"]),
                "updated_at": str(product_row["updated_at"]),
            })
    return result

if __name__ == "__main__":
    uvicorn.run("hybrid_recommender:app", host="0.0.0.0", port=8001, reload=True)