# backend/app/core/post_call_processor.py

import uuid
from typing import List, Dict, Any
from .schemas import VapiMessageOpenAI 
from .llm_factory import get_llm
from .tools import case_intake_extractor # We'll reuse our powerful extractor
# Import our database and cases table object
from .database import database, cases
import json # For handling JSON data correctly

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

async def process_call_transcript(final_transcript: List[VapiMessageOpenAI]):
    """
    Main function to process the final transcript after a call ends.
    1. Generates a new Case ID.
    2. Formats the transcript into a single string.
    3. Extracts structured data using the Case Intake tool.
    4. Generates a narrative summary.
    5. Compiles everything into a final "Case File" object.
    """
    if not final_transcript:
        print("--- No transcript data to process. ---")
        return

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
        query = cases.insert().values(
            case_id=case_id,
            status="Pending Review",
            # SQLAlchemy expects a JSON string, not a dict, for a JSON column
            structured_intake=json.dumps(structured_data),
            call_summary=summary,
            full_transcript=transcript_text,
        )
        # Execute the query asynchronously
        last_record_id = await database.execute(query)
        print(f"--- Successfully saved case {case_id} with DB record id {last_record_id}. ---")

    except Exception as e:
        print(f"--- DATABASE ERROR: Failed to save case file. Error: {e} ---")
    return case_file