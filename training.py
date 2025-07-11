# training_pipeline.py
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from mlxtend.frequent_patterns import apriori, association_rules
import mlflow

def run_training_pipeline(products, cart_items, df_trans):
    mlflow.set_experiment("Hybrid_Recommendation_System")
    with mlflow.start_run(run_name="training_pipeline"):

        tfidf = TfidfVectorizer(stop_words="english")
        tfidf_matrix = tfidf.fit_transform(products["text"])
        cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)
        id_to_index = pd.Series(products.index, index=products["id"])

        with open("artifacts/tfidf_vocab.txt", "w") as f:
            for word in tfidf.get_feature_names_out():
                f.write(f"{word}\n")
        mlflow.log_artifact("artifacts/tfidf_vocab.txt")

        user_item_matrix = cart_items.groupby(["cart_id", "name"])["quantity"].sum().unstack().fillna(0)
        item_user_matrix = user_item_matrix.T
        item_sim = cosine_similarity(item_user_matrix)
        item_sim_df = pd.DataFrame(item_sim, index=item_user_matrix.index, columns=item_user_matrix.index)

        min_support = 0.01
        mlflow.log_param("min_support", min_support)

        frequent_itemsets = apriori(df_trans.astype("bool"), min_support=min_support, use_colnames=True)
        rules_df = association_rules(frequent_itemsets, metric="lift", min_threshold=0.5)
        rules_df = rules_df[["antecedents", "consequents", "support", "confidence", "lift"]]

        mlflow.log_metric("num_rules", len(rules_df))

        pd.DataFrame(cosine_sim).to_csv("artifacts/cosine_sim.csv", index=False)
        item_sim_df.to_csv("artifacts/item_sim_df.csv")
        rules_df.to_csv("artifacts/rules.csv", index=False)

        mlflow.log_artifact("artifacts/cosine_sim.csv")
        mlflow.log_artifact("artifacts/item_sim_df.csv")
        mlflow.log_artifact("artifacts/rules.csv")

        return cosine_sim, id_to_index, item_sim_df, rules_df
