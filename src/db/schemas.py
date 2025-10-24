# src/db/schemas.py
from pydantic import BaseModel
from typing import Optional, List

class Conversation(BaseModel):
    """Pydantic model for validating incoming conversation data."""
    message_id: str
    user_id: str
    campaign_id: str
    timestamp: str 
    intent: str
    message: str
    
    # Optional field for the pipeline to add
    embedding: Optional[List[float]] = None