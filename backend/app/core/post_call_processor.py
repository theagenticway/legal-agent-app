# backend/app/core/post_call_processor.py

import uuid
from typing import List, Dict, Any, Optional
from .schemas import VapiMessageOpenAI 
from .llm_factory import get_llm
from .tools import case_intake_extractor # We'll reuse our powerful extractor
# Import our database and cases table object
from .database import database, cases
import json # For handling JSON data correctly
from sqlalchemy import select, update
from datetime import datetime
def format_transcript_for_llm(transcript_messages: List[VapiMessageOpenAI]) -> str:
    """
    Takes the list of message objects from Vapi and formats it into a single
    human-readable string.
    """
    formatted_string = ""
    for message in transcript_messages:
        role = message.role.capitalize() if message.role else "Unknown"
        content = message.content.strip() if message.content else ""
        
        if content:
            formatted_string += f"{role}: {content}\n"
    return formatted_string

def generate_summary_and_notes(full_transcript_string: str) -> str:
    """
    Uses an LLM to generate a concise summary of the call.
    """
    print("--- Generating call summary ---")
    llm = get_llm(temperature=0.2)
    
    prompt = f"""
    You are a highly skilled paralegal. Based on the following call transcript, please provide a concise, neutral summary of the conversation.
    Focus on the key issues discussed and the main purpose of the call.

    Transcript:
    ---
    {full_transcript_string}
    ---

    Summary:
    """
    
    response = llm.invoke(prompt)
    return response.content

async def process_call_transcript(final_transcript: List[VapiMessageOpenAI], caller_phone_number: str, vapi_call_id: Optional[str]):
    """
    Main function to process the final transcript after a call ends.
    1. Generates a new Case ID.
    2. Formats the transcript into a single string.
    3. Extracts structured data using the Case Intake tool.
    4. Generates a narrative summary.
    5. Compiles everything into a final "Case File" object.
    6. Saves the case file to the database."""
    # --- 1. Prevent duplicate processing of the SAME call ---
    if vapi_call_id:
        query = select(cases).where(cases.c.vapi_call_id == vapi_call_id)
        if await database.fetch_one(query):
            print(f"--- Duplicate webhook for call {vapi_call_id}. Skipping. ---")
            return
    if not final_transcript:
        print("--- No transcript data to process. ---")
        return
    
# --- 2. Check for EXISTING cases from this caller ---
    # Find the most recent case for this phone number
    query = select(cases).where(cases.c.caller_phone_number == caller_phone_number).order_by(cases.c.created_at.desc())
    existing_case = await database.fetch_one(query)

    transcript_text = format_transcript_for_llm(final_transcript)
    summary = generate_summary_and_notes(transcript_text)

    # --- 3. DECIDE: Update existing case or Insert new one ---
    if existing_case:
        # --- UPDATE LOGIC ---
        print(f"--- Found existing case {existing_case.case_id} for caller. Appending note. ---")
        
        # Create a new note object
        new_note = {
            "timestamp": datetime.utcnow().isoformat(),
            "vapi_call_id": vapi_call_id,
            "summary": summary,
            "transcript": transcript_text
        }
        
        # Get existing notes, or initialize an empty list
        existing_notes = existing_case.follow_up_notes or []
        if isinstance(existing_notes, str): # Handle case where DB returns JSON as string
            existing_notes = json.loads(existing_notes)
            
        existing_notes.append(new_note)
        
        # Create and execute the UPDATE query
        update_query = (
            update(cases)
            .where(cases.c.id == existing_case.id)
            .values(follow_up_notes=existing_notes)
        )
        
        try:
            await database.execute(update_query)
            print(f"--- Successfully appended note to case {existing_case.case_id}. ---")
        except Exception as e:
            print(f"--- DATABASE UPDATE ERROR: {e} ---")

    else:
        # --- INSERT LOGIC (for the first time a caller calls) ---
        # 1. Generate a unique Case ID
        case_id = f"CASE-{uuid.uuid4().hex[:8].upper()}"
        print(f"--- Processing new case: {case_id} ---")

        # 2. Format the raw transcript messages into a single block of text
        transcript_text = format_transcript_for_llm(final_transcript)
        
        # 3. Use our existing tool to extract structured data
        # This is a great example of code reuse!
        structured_data = case_intake_extractor(transcript_text)

        # 4. Generate a narrative summary of the call
        summary = generate_summary_and_notes(transcript_text)
        
        # 5. Compile the final "Case File"
        case_file = {
            "caseId": case_id,
            "status": "Pending Review",
            "structuredIntake": structured_data,
            "callSummary": summary,
            "fullTranscript": transcript_text
        }
        
        # --- SIMULATE SAVING TO DATABASE ---
        # In a real application, you would now save the 'case_file' object
        # to your PostgreSQL, MongoDB, or other database.
        # For now, we will just print it to the console.
        print("\n--- COMPILED CASE FILE ---")
        import json
        print(json.dumps(case_file, indent=2))
        print("--------------------------\n")
        try:
            print(f"--- Attempting to save case {case_id} to the database. ---")
            insert_query = cases.insert().values(
                case_id=case_id,
                caller_phone_number=caller_phone_number, # <-- Save the number
                status="Pending Review",
                # SQLAlchemy expects a JSON string, not a dict, for a JSON column
                structured_intake=json.dumps(structured_data),
                call_summary=summary,
                full_transcript=transcript_text,
                # The transcript of the FIRST call
                follow_up_notes=[] # Initialize with an empty list
            )
            # Execute the query asynchronously
            last_record_id = await database.execute(insert_query)
            print(f"--- Successfully saved case {case_id} with DB record id {last_record_id}. ---")

        except Exception as e:
            print(f"--- DATABASE ERROR: Failed to save case file. Error: {e} ---")
        return case_file