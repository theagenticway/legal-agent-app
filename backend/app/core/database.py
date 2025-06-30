# backend/app/core/database.py
import os
from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    JSON
)
from sqlalchemy.sql import func
from databases import Database
from sqlalchemy.dialects.postgresql import JSONB

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
metadata = MetaData()

# Define the 'cases' table (existing)
cases = Table(
    "cases",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("case_id", String(50), unique=True, nullable=False),
    Column("caller_phone_number", String(50)),
    Column("status", String(50), default="Pending Review"),
    Column("structured_intake", JSON),
    Column("call_summary", Text),
    Column("full_transcript", Text),
    Column("follow_up_notes", JSONB),
    Column("created_at", DateTime, default=func.now(), nullable=False),
    Column("vapi_call_id", String(100), nullable=True),
)

# --- NEW TABLE: indexed_rag_documents ---
indexed_rag_documents = Table(
    "indexed_rag_documents",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("filename", String(255), nullable=False),
    Column("num_chunks", Integer, nullable=True),
    Column("indexed_at", DateTime, default=func.now(), nullable=False),
    Column("source_path", String(512), nullable=True) # Optional: if you want to store original path
)

database = Database(DATABASE_URL)

def create_db_and_tables():
    metadata.create_all(engine)