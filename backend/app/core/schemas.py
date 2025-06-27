# backend/app/core/schemas.py

from pydantic import BaseModel, Field
from typing import Optional, List

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