# backend/app/core/schemas.py

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime # NEW

# Existing Case Intake
class CaseIntake(BaseModel):
    """
    A Pydantic model to define the structured data for a new case.
    The descriptions are crucial, as they will guide the LLM's extraction process.
    """
    client_name: str = Field(description="The full name of the primary client.")
    opposing_party: Optional[str] = Field(description="The full name of the opposing party or entity, if mentioned.")
    case_type: str = Field(description="A brief, high-level classification of the case (e.g., 'Contract Dispute', 'Intellectual Property', 'Personal Injury', 'Wrongful Termination').")
    summary_of_facts: str = Field(description="A concise, one to two-paragraph summary of the key events and facts of the case as described in the input text.")
    key_dates: List[str] = Field(description="A list of important dates mentioned in the text, in MM/DD/YYYY format if possible.", default=[])

# VAPI MODELS (Keep these here)
class VapiMessageOpenAI(BaseModel):
    role: str
    content: Optional[str] = None

class VapiArtifact(BaseModel):
    messagesOpenAIFormatted: List[VapiMessageOpenAI]

class VapiPayload(BaseModel):
    type: str
    status: Optional[str] = None
    endedReason: Optional[str] = None
    artifact: Optional[VapiArtifact] = None
    conversation: Optional[List[VapiMessageOpenAI]] = None
    call: Optional[Dict[str, Any]] = None

class VapiWebhookRequest(BaseModel):
    message: VapiPayload

# --- NEW DASHBOARD-RELATED SCHEMAS ---

class OverviewCounts(BaseModel):
    active_contracts: int
    upcoming_deadlines: int
    new_notifications: int

class RecentActivity(BaseModel):
    id: int
    description: str
    activity_type: str
    performed_at: datetime

class UpcomingDeadline(BaseModel):
    id: int
    title: str
    task_type: str
    due_date: datetime
    status: str

class Notification(BaseModel):
    id: int
    message: str
    notification_type: str
    is_read: bool
    created_at: datetime
    related_url: Optional[str] = None # Link to the relevant item

# You might want a simple schema for the full dashboard data response
class DashboardData(BaseModel):
    overview: OverviewCounts
    recent_activity: List[RecentActivity]
    upcoming_deadlines: List[UpcomingDeadline]
    notifications: List[Notification]