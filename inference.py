# inference_pipeline.py
import pandas as pd
from collections import defaultdict
import mlflow

def hybrid_recommend(cart_ids, cart_names, products, rules_df, cosine_sim, id_to_index, item_sim_df, weights=None):
    mlflow.set_experiment("Hybrid_Recommendation_System")
    with mlflow.start_run(run_name="inference_pipeline"):
        if weights is None:
            weights = {"market": 0.4, "content": 0.3, "collab": 0.3}
        mlflow.log_params(weights)

        score = defaultdict(float)

        # Market-based
        for item in cart_names:
            matched = rules_df[rules_df["antecedents"].apply(lambda x: item in x)]
            for conseq in matched["consequents"]:
                for name in conseq:
                    score[name] += weights["market"]

        # Content-based
        for pid in cart_ids:
            if pid in id_to_index:
                idx = id_to_index[pid]
                sim_scores = list(enumerate(cosine_sim[idx]))
                for i, s in sim_scores[1:11]:
                    name = products.iloc[i]["name"]
                    score[name] += weights["content"] * s

        # Collaborative
        for name in cart_names:
            if name in item_sim_df.columns:
                sims = item_sim_df[name].sort_values(ascending=False)[1:11]
                for sim_name, val in sims.items():
                    score[sim_name] += weights["collab"] * val

        top_recs = sorted(score.items(), key=lambda x: x[1], reverse=True)[:10]
        mlflow.log_metric("num_recommendations", len(top_recs))

        name_to_id = products.set_index("name")["id"].to_dict()
        result = []
        for name, _ in top_recs:
            if name in name_to_id:
                row = products[products["id"] == name_to_id[name]].iloc[0]
                result.append({
                    "id": int(row["id"]),
                    "name": row["name"],
                    "description": row["description"],
                    "price": float(row["price"]) if not pd.isna(row["price"]) else None,
                    "image_urls": row["image_urls"].split(",") if pd.notna(row["image_urls"]) else []
                })

        pd.DataFrame(result).to_csv("artifacts/recommendations.csv", index=False)
        mlflow.log_artifact("artifacts/recommendations.csv")
        return result
