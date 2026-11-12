# src/api/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# 1. Login Request & Response
class LoginRequest(BaseModel):
    username: str = Field(..., example="alice", description="User login ID")
    password: str = Field(..., example="tech123", description="User password")

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    allowed_departments: List[str]

# 2. Chat Query Request
class ChatRequest(BaseModel):
    query: str = Field(
        ..., 
        min_length=1, 
        max_length=500, 
        example="What are FinSolve's disaster recovery targets?",
        description="The question asked to the enterprise assistant"
    )

# 3. Chat Query Response
class DocumentSource(BaseModel):
    source: str
    department: str
    rerank_score: float

class ChatResponse(BaseModel):
    query: str
    answer: str
    user: str
    role: str
    status: str
    latency_seconds: float
    token_usage: Dict[str, int]
    sources: List[DocumentSource]

# 4. Health Check
class HealthResponse(BaseModel):
    status: str
    chroma_db_connected: bool
    models_loaded: bool