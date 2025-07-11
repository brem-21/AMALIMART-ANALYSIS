# feature_pipeline.py
import pandas as pd
from mlxtend.preprocessing import TransactionEncoder
import mlflow
import os

def run_feature_pipeline(product_path, cart_path):
    mlflow.set_experiment("Hybrid_Recommendation_System")
    with mlflow.start_run(run_name="feature_pipeline"):
        os.makedirs("artifacts", exist_ok=True)
        products = pd.read_excel(product_path, sheet_name="products")
        cart_items = pd.read_excel(cart_path, sheet_name="cart_items")

        products = products[products["status"] == "ACTIVE"].copy()
        products["text"] = products["name"].fillna("") + " " + products["description"].fillna("")

        cart_items = cart_items[cart_items["product_id"].isin(products["id"])]
        cart_items = cart_items.merge(products[["id", "name"]], left_on="product_id", right_on="id")

        transactions = cart_items.groupby("cart_id")["name"].apply(list).tolist()
        te = TransactionEncoder()
        te_array = te.fit(transactions).transform(transactions)
        df_trans = pd.DataFrame(te_array, columns=te.columns_)

        products.to_csv("artifacts/products.csv", index=False)
        cart_items.to_csv("artifacts/cart_items.csv", index=False)
        df_trans.to_csv("artifacts/transactions.csv", index=False)

        mlflow.log_artifact("artifacts/products.csv")
        mlflow.log_artifact("artifacts/cart_items.csv")
        mlflow.log_artifact("artifacts/transactions.csv")

        return products, cart_items, df_trans
