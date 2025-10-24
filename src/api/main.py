import logging
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from sentence_transformers import SentenceTransformer
import time
import json

from src.utils.db import (
    get_redis_client, 
    get_milvus_connection, 
    get_neo4j_driver,
    get_sqlite_conn,
    get_mongo_client
)
from src.utils import config

# --- Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a state dictionary to hold our DB connections and model
app_state = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load DB connections and ML model on startup."""
    logger.info("API starting up...")
    app_state["redis"] = get_redis_client()
    app_state["milvus"] = get_milvus_connection()
    app_state["neo4j"] = get_neo4j_driver()
    app_state["mongo"] = get_mongo_client()
    app_state["model"] = SentenceTransformer(config.EMBEDDING_MODEL)
    logger.info("Connections and ML model loaded. API is ready. ✅")
    yield
    # Clean up on shutdown
    logger.info("API shutting down...")
    app_state["neo4j"].close()

app = FastAPI(lifespan=lifespan)

# --- Middleware for Observability ---
@app.middleware("http")
async def add_process_time_header(request, call_next):
    """Log API latency for monitoring."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.4f}s")
    return response

# --- Helper Functions for Retrieval ---

def get_user_query_vector(user_id: str):
    """
    Creates a query vector for a user by fetching one of their
    recent messages from Mongo and embedding it.
    """
    mongo = app_state["mongo"]
    model = app_state["model"]
    
    # 1. Get a recent message from Mongo
    recent_message = mongo.conversations.find_one({"user_id": user_id})
    if not recent_message:
        return None # User not found
        
    # 2. Generate embedding
    query_vector = model.encode(recent_message['message'], convert_to_numpy=True).tolist()
    return query_vector


def search_similar_users(query_vector: list[float], k: int = 5) -> list[str]:
    """Finds top-k similar messages and returns their user_ids[cite: 51]."""
    milvus = app_state["milvus"]
    search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
    
    results = milvus.search(
        data=[query_vector],
        anns_field="embedding",
        param=search_params,
        limit=k,
        output_fields=["user_id"] # We only need the user_id
    )
    
    similar_user_ids = [hit.entity.get("user_id") for hit in results[0]]
    # Remove duplicates
    return list(set(similar_user_ids))


def fetch_campaigns_for_users(user_ids: list[str]) -> list[str]:
    """Finds campaigns connected to a list of users in Neo4j[cite: 52]."""
    neo_driver = app_state["neo4j"]
    with neo_driver.session() as session:
        result = session.run("""
        MATCH (u:User)-[:PARTICIPATED_IN]->(c:Campaign)
        WHERE u.id IN $user_ids
        RETURN DISTINCT c.id AS campaign_id
        """, user_ids=user_ids)
        return [record["campaign_id"] for record in result]


def rank_campaigns_by_engagement(campaign_ids: list[str]) -> list[dict]:
    """Ranks campaigns by total engagement score from SQLite[cite: 53]."""
    # We must create a new connection here as SQLite conns can't be shared across threads
    conn = get_sqlite_conn()
    cursor = conn.cursor()
    
    # Build a safe query (no SQL injection)
    placeholders = ",".join("?" for _ in campaign_ids)
    query = f"""
    SELECT campaign_id, SUM(engagement_count) as total_engagement
    FROM user_analytics
    WHERE campaign_id IN ({placeholders})
    GROUP BY 1
    ORDER BY 2 DESC
    """
    
    results = cursor.execute(query, campaign_ids).fetchall()
    conn.close()
    return [{"campaign_id": row[0], "ranking_score": row[1]} for row in results]


# --- API Endpoint ---

@app.get("/recommendations/{user_id}")
async def get_recommendations(user_id: str):
    """
    Generates personalized campaign recommendations for a user
    using a hybrid retrieval approach[cite: 49].
    """
    redis = app_state["redis"]
    cache_key = f"rec:{user_id}"

    # 1. Check Cache [cite: 28]
    try:
        cached_result = redis.get(cache_key)
        if cached_result:
            logger.info(f"Cache HIT for user {user_id}")
            return {
                "user_id": user_id,
                "recommendations": json.loads(cached_result),
                "retrieval_source": "cache"
            }
    except Exception as e:
        logger.warning(f"Redis cache read failed: {e}")

    logger.info(f"Cache MISS for user {user_id}. Computing...")
    
    # 2. Get Query Vector
    query_vector = get_user_query_vector(user_id)
    if not query_vector:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found or has no data.")

    # 3. Retrieve (Hybrid Search)
    # (a) Milvus Vector Search -> Similar Users
    similar_user_ids = search_similar_users(query_vector)
    logger.info(f"Found similar users: {similar_user_ids}")
    
    # (b) Neo4j Graph Search -> Campaigns
    if not similar_user_ids:
        logger.warning(f"No similar users found for {user_id}")
        return {"user_id": user_id, "recommendations": [], "retrieval_source": "computed"}
        
    campaign_ids = fetch_campaigns_for_users(similar_user_ids)
    logger.info(f"Found related campaigns: {campaign_ids}")

    # (c) SQLite Analytical Rank -> Rank
    if not campaign_ids:
        logger.warning(f"No campaigns found for similar users of {user_id}")
        return {"user_id": user_id, "recommendations": [], "retrieval_source": "computed"}
        
    ranked_campaigns = rank_campaigns_by_engagement(campaign_ids)
    logger.info(f"Ranked campaigns: {ranked_campaigns}")
    
    # 4. Cache & Return
    final_recs = [
        {**item, "reason": "Recommended based on users with similar interests."}
        for item in ranked_campaigns
    ]
    
    try:
        redis.set(cache_key, json.dumps(final_recs), ex=config.RECOMMENDATION_CACHE_TTL_SECONDS)
    except Exception as e:
        logger.warning(f"Redis cache write failed: {e}")

    return {
        "user_id": user_id,
        "recommendations": final_recs,
        "retrieval_source": "computed"
    }

@app.get("/")
def read_root():
    return {"message": "AI Marketing API is running! Visit /docs for endpoints."}