# src/utils/db.py
from pymongo import MongoClient
from redis import Redis
from neo4j import GraphDatabase
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType
from pymilvus import utility
from src.utils import config
import sqlite3
import time
import logging
from pymilvus.exceptions import MilvusException


logger = logging.getLogger(__name__)

def get_mongo_client():
    """Returns a MongoDB client instance."""
    client = MongoClient(config.MONGO_HOST, config.MONGO_PORT)
    return client.marketing_db # Return the specific database

def get_redis_client():
    """Returns a Redis client instance."""
    return Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, decode_responses=True)

def get_neo4j_driver():
    """Returns a Neo4j driver instance."""
    uri = f"bolt://{config.NEO4J_HOST}:{config.NEO4J_BOLT_PORT}"
    return GraphDatabase.driver(uri, auth=(config.NEO4J_USER, config.NEO4J_PASS))

def get_milvus_connection():
    """Connects to Milvus with a retry mechanism AND ensures correct schema."""
    
    retries = 10
    wait_time = 5  # seconds
    
    for i in range(retries):
        try:
            logger.info(f"Attempting to connect to Milvus ({i+1}/{retries})...")
            connections.connect("default", host=config.MILVUS_HOST, port=config.MILVUS_PORT)
            logger.info("Milvus connection successful! ✅")
            break  # Success! Exit the loop.
        except MilvusException as e:
            if "server unavailable" in str(e) or "connecting" in str(e):
                logger.warning(f"Milvus not ready yet: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"A non-retryable Milvus error occurred: {e}")
                raise e
    else:
        logger.error(f"Could not connect to Milvus after {retries} attempts.")
        raise ConnectionError("Failed to connect to Milvus.")

    # --- Schema setup ---
    collection_name = config.MILVUS_COLLECTION_NAME

    # --------------------------------------------------------------------
    # --- THIS IS THE FIX ---
    # Drop the collection if it exists. This destroys the old, broken
    # schema (dim 768) and allows us to create a new one (dim 384).
    if utility.has_collection(collection_name):
        logger.warning(f"Dropping existing Milvus collection '{collection_name}' to ensure schema is correct.")
        utility.drop_collection(collection_name)
        logger.info(f"Collection '{collection_name}' dropped.")
    # --- END FIX ---
    # --------------------------------------------------------------------

    
    # Define collection schema
    fields = [
        FieldSchema(name="message_id", dtype=DataType.VARCHAR, is_primary=True, max_length=100),
        FieldSchema(name="user_id", dtype=DataType.VARCHAR, max_length=100),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=config.EMBEDDING_DIM) # This will now use 384
    ]
    schema = CollectionSchema(fields, "Conversation embeddings")
    
    # Create collection (it is now guaranteed to be new)
    logger.info(f"Creating new collection '{collection_name}' with dim={config.EMBEDDING_DIM}.")
    collection = Collection(collection_name, schema)
    
    # Create an index
    if not collection.has_index():
        logger.info(f"Creating index for collection '{collection_name}'...")
        index_params = {
            "metric_type": "L2",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 1024}
        }
        collection.create_index("embedding", index_params)
        logger.info("Index created.")
    
    logger.info("Loading Milvus collection...")
    collection.load()
    logger.info("Milvus collection loaded.")
    return collection

def get_sqlite_conn():
    """Returns a connection to the SQLite analytics DB."""
    conn = sqlite3.connect("/db/analytics.db") # This uses the shared volume
    
    # Create table if it doesn't exist
    conn.execute("""
    CREATE TABLE IF NOT EXISTS user_analytics (
        user_id VARCHAR(100),
        campaign_id VARCHAR(100),
        engagement_count INTEGER,
        PRIMARY KEY (user_id, campaign_id)
    );
    """)
    return conn