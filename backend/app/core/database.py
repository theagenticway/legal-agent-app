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
# Get the database URL from environment variables set in docker-compose.yml
DATABASE_URL = os.getenv("DATABASE_URL")

# SQLAlchemy engine
engine = create_engine(DATABASE_URL)
metadata = MetaData()

# Define the 'cases' table
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

# Databases library for async connections
database = Database(DATABASE_URL)

# Function to create the table
def create_db_and_tables():
    metadata.create_all(engine)