
# AmaliMart Recommendation API

The **AmaliMart Recommendation API** delivers product recommendations powered by a **hybrid engine** that combines:

-  **Market-Based** (Apriori association rules)
-  **Content-Based** (TF-IDF + cosine similarity)
-  **Collaborative Filtering** (user-item cart behavior)

This API allows clients to request personalized product suggestions using one or more cart IDs.

---

##  Recommendation Flow

1. **Cart Identification**:  
   Clients send a list of cart IDs as query parameters.

2. **Data Aggregation**:  
   The API fetches cart item data and joins it with relevant product metadata (e.g., name, description).

3. **Recommendation Engines**:
   - **Market-Based**: Uses the Apriori algorithm to detect frequently co-purchased items.
   - **Content-Based**: Applies TF-IDF vectorization and cosine similarity on product metadata.
   - **Collaborative Filtering**: Computes item-to-item similarity using historical cart quantities.

4. **Hybrid Scoring**:  
   Each candidate product is scored using a **weighted average** of the three engines.

5. **Response**:  
   Returns a list of recommended products ranked by **hybrid score**.

---

##  API Endpoint

###  `GET /recommendations`

Generates a list of product recommendations.

###  Query Parameters

| Parameter | Type       | Description                                      | Validation                                 | Required |
|-----------|------------|--------------------------------------------------|---------------------------------------------|----------|
| cart_ids  | List[Int]  | One or more cart IDs to base recommendations on  | Must be integers and exist in `cart_items` |  Yes    |

###  Example Request

```http
GET /recommendations?cart_ids=1&cart_ids=2&cart_ids=3
```

---

##  Success Response

**Status Code**: `200 OK`

```json
{
  "success": true,
  "message": "Recommendations generated successfully",
  "timestamp": "2025-07-24T14:45:10.123Z",
  "data": [
    {
      "id": 101,
      "name": "Wireless Headphones",
      "description": "High-quality sound with noise cancellation",
      "sku": "WH-2025",
      "price": 149.99,
      "stock_quantity": 25,
      "weight": 0.5,
      "status": "ACTIVE",
      "vendor_id": 12,
      "low_stock_threshold": 5,
      "min_order_quantity": 1,
      "average_rating": 4.7,
      "thumbnail_url": "https://cdn.amalimart.com/images/headphones_thumb.jpg",
      "image_urls": [
        "https://cdn.amalimart.com/images/headphones_1.jpg",
        "https://cdn.amalimart.com/images/headphones_2.jpg"
      ],
      "is_active": true,
      "created_at": "2024-06-01T10:15:00Z",
      "updated_at": "2025-01-12T18:30:00Z"
    }
  ]
}
```

---

##  Error Responses

###  Missing or Invalid Cart IDs

**Status Code**: `422 Unprocessable Entity`

```json
{
  "detail": [
    {
      "loc": ["query", "cart_ids"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 🛠 Internal Server Error

**Status Code**: `500 Internal Server Error`

```json
{
  "success": false,
  "message": "Failed to generate recommendations",
  "timestamp": "2025-07-24T14:45:10.123Z",
  "data": {}
}
```

---

##  Security & Validation

-  **HTTPS Required**: All requests must use HTTPS.
-  **Validation Rules**:
  - `cart_ids` must be valid integers.
  - `cart_ids` must exist in the database (`cart_items` table).

---

##  Implementation Notes

###  Engine Composition

| Engine              | Technique                                  | Library              |
|---------------------|--------------------------------------------|----------------------|
| Market-Based        | Apriori + Association Rules                | `mlxtend`            |
| Content-Based       | TF-IDF Vectorizer + Cosine Similarity      | `scikit-learn`       |
| Collaborative Filter| Item-to-item matrix similarity             | `scikit-learn`       |

###  Ranking Logic

```
Final Score = 0.4 * Market-Based Score
            + 0.3 * Content-Based Score
            + 0.3 * Collaborative Score
```

###  Product Filtering

Only products with `status='ACTIVE'` are returned.

---

##  Tech Stack

- `FastAPI`
- `pandas`
- `mlxtend`
- `scikit-learn`
- `uvicorn`
- `mysql-connector-python`

---
