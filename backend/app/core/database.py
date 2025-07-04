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
    JSON,
    Boolean,
    ForeignKey # No change here, correct
)
from sqlalchemy.sql import func
from databases import Database
from sqlalchemy.dialects.postgresql import JSONB

DATABASE_URL = os.getenv("DATABASE_URL")

# Ensure the engine uses the correct driver for databases library (asyncpg)
# databases library handles the connection string parsing for the driver.
engine = create_engine(DATABASE_URL)
metadata = MetaData()


# Define the 'cases' table (updated)
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
    Column("assigned_to", String(255), nullable=True), # NEW: Added assigned_to
    Column("last_updated_at", DateTime, default=func.now(), onupdate=func.now(), nullable=False), # NEW: Added last_updated_at
)

# --- NEW TABLE: indexed_rag_documents (existing) ---
indexed_rag_documents = Table(
    "indexed_rag_documents",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("filename", String(255), nullable=False),
    Column("num_chunks", Integer, nullable=True),
    Column("indexed_at", DateTime, default=func.now(), nullable=False),
    Column("source_path", String(512), nullable=True)
)

# --- NEW TABLE: clients ---
clients = Table(
    "clients",
    metadata,
    Column("id", Integer, primary_key=True),
    # client_id is now explicitly generated in main.py before insert.
    # So remove the 'default' here to accurately reflect its handling.
    Column("client_id", String(50), unique=True, nullable=False), # No default here
    Column("name", String(255), nullable=False),
    Column("contact_email", String(255), unique=True, nullable=False),
    Column("phone_number", String(50), unique=True, nullable=True),
    Column("status", String(50), default="Active"), # Active, Inactive, etc.
    Column("last_activity_at", DateTime, default=func.now(), nullable=False),
    Column("created_at", DateTime, default=func.now(), nullable=False),
    Column("notes", Text, nullable=True)
)

# --- NEW TABLE: contracts ---
contracts = Table(
    "contracts",
    metadata,
    Column("id", Integer, primary_key=True),
    # contract_id is now explicitly generated in main.py before insert.
    # So remove the 'default' here to accurately reflect its handling.
    Column("contract_id", String(50), unique=True, nullable=False), # No default here
    Column("client_id", Integer, ForeignKey("clients.id"), nullable=True), # Link to clients
    Column("name", String(255), nullable=False),
    Column("status", String(50), default="Active"), # Active, Review, Expired, etc.
    Column("signed_date", DateTime, nullable=True),
    Column("expiration_date", DateTime, nullable=True),
    Column("last_reviewed_at", DateTime, nullable=True),
    Column("created_at", DateTime, default=func.now(), nullable=False)
)

# --- NEW TABLE: activities ---
activities = Table(
    "activities",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("description", String(512), nullable=False),
    Column("activity_type", String(50), nullable=False), # e.g., "Contract Review", "Legal Research", "Case Management"
    Column("related_id", Integer, nullable=True), # Optional: ID of related contract/case/document
    Column("related_type", String(50), nullable=True), # Optional: "contract", "case", "document"
    Column("performed_at", DateTime, default=func.now(), nullable=False)
)

# --- NEW TABLE: tasks (for deadlines and general tasks) ---
tasks = Table(
    "tasks",
    metadata,
    Column("id", Integer, primary_key=True),
    # task_id is now explicitly generated in main.py before insert.
    # So remove the 'default' here to accurately reflect its handling.
    Column("task_id", String(50), unique=True, nullable=False), # No default here
    Column("title", String(255), nullable=False),
    Column("description", Text, nullable=True),
    Column("due_date", DateTime, nullable=True),
    Column("status", String(50), default="Pending"), # Pending, In Progress, Completed, Overdue
    Column("task_type", String(50), nullable=False), # e.g., "Review", "Prepare", "Report", "Deposition"
    Column("assigned_to", String(255), nullable=True), # e.g., "Alex", "Sarah Johnson"
    Column("related_case_id", Integer, ForeignKey("cases.id"), nullable=True), # Link to cases
    Column("created_at", DateTime, default=func.now(), nullable=False),
    Column("completed_at", DateTime, nullable=True)
)

# --- NEW TABLE: notifications ---
notifications = Table(
    "notifications",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("message", String(512), nullable=False),
    Column("notification_type", String(50), nullable=False), # e.g., "Contract Review", "Legal Research", "Case Status"
    Column("is_read", Boolean, default=False, nullable=False),
    Column("related_url", String(512), nullable=True), # URL to link to relevant item (e.g., case page)
    Column("created_at", DateTime, default=func.now(), nullable=False)
)


database = Database(DATABASE_URL)

def create_db_and_tables():
    print("--- Creating database tables if they don't exist ---")
    try:
        # We need to drop existing tables and recreate them if you've changed
        # `nullable` or `default` constraints on columns that already exist.
        # This is a DESTRUCTIVE operation and will wipe your existing data.
        # Use with CAUTION in development, and NEVER in production without a migration strategy.
        # metadata.drop_all(engine) # Uncomment this if you want to wipe and recreate
        metadata.create_all(engine)
        print("--- Database tables created/checked successfully ---")
    except Exception as e:
        print(f"Error creating database tables: {e}")
        # In a real app, you might want to log this more verbosely or exit