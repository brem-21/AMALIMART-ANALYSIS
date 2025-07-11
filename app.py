# api.py
from fastapi import FastAPI, Query
from typing import List
import uvicorn

from feature_pipeline import run_feature_pipeline
from training import run_training_pipeline
from inference import hybrid_recommend

app = FastAPI()

product_path = "./data/realistic_ecommerce_data_updated.xlsx"
cart_path = "./data/realistic_ecommerce_data_updated.xlsx"

products, cart_items, df_trans = run_feature_pipeline(product_path, cart_path)
cosine_sim, id_to_index, item_sim_df, rules_df = run_training_pipeline(products, cart_items, df_trans)

@app.get("/recommendations")
def recommend(cart_ids: List[int] = Query(...)):
    cart_subset = cart_items[cart_items["cart_id"].isin(cart_ids)]
    cart_names = cart_subset["name"].tolist()
    cart_ids_ = cart_subset["product_id"].tolist()
    return hybrid_recommend(cart_ids_, cart_names, products, rules_df, cosine_sim, id_to_index, item_sim_df)

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8001, reload=True)

