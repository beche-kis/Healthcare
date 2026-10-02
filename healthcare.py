# Multi-Agent Healthcare Traige System

import json
import os
import re 
import time
import logging 
from datetime import datetime
from dotenv import load_dotenv 
from strands import Agent, tool
from strands.models import BedrockModel 
from utils import clean_response,run_agent_with_retry,_tool_results
from Agents import build_symptom_analyzer,build_urgency_classifier,build_urgency_classifier,build_appointment_scheduler,PATIENT_COMPLAINTS,AVAILABLE_SLOTS,SYMPTOM_CONDITIONS 


load_dotenv()

logging.basicConfig(level= logging.WARNING)
logger = logging.getLogger(__name__)

#Configuration 

AWS_REGION = os.environ.get("AWS_REGION" ,"us-east-1")
MODEL_ID = os.environ.get("MODEL_ID" , "us.anthropic.claude-sonnet-4-5-20250929-v1:0")






# Main orchestartor 

def run_triage_pipeline(patient: dict) ->dict:
    """Run the 3 agents pipeline for a single patient.

    Flow: SymptomAnalyzer ->UrgencyClassifier -> Appointment Booking

    Each agent is instantiated fresh to avoid context bleed between patients.

    The cooordinator passes the outputs of one agent as input to the next.
    """

    print("     [1/3] Symptom Analyzer...")

    _tool_results.clear()
    run_agent_with_retry(
        build_symptom_analyzer,
        f"Analyze these symptoms:{patient['complaint']}"
    )

    symptom_json = json.loads(_tool_results.get("symptoms",'{"total_matches":0}'))

    symptom_str= json.dumps(symptom_json)

    print(f"Matched {symptom_json.get('total_matches',0)} symptoms")

    print("     [2/3]\ Urgency Classifier...")
    run_agent_with_retry(
        build_urgency_classifier,
        f"Classify urgency for this symptom analysis: {symptom_str}"

        )
    urgency_json = json.loads(_tool_results.get("urgency",'{"urgency":"routine"}'))

    urgency_level = urgency_json.get("urgency","routine")
    print(f"  Urgency:{urgency_level}")

    print("    [3/3] Appontment Booked...")
    run_agent_with_retry(
        build_appointment_scheduler,
        f"Book an appointment for patient_id = {patient['patient_id']} with urgency_level = {urgency_level}")

    booking_json = json.loads(_tool_results.get("booking",'{"status":"failed"}'))
    print(f" Slot: {booking_json.get("time_slot",'N/A')}")
    return {
         "patient": patient["name"],
        "symptoms": symptom_json,
        "urgency" :urgency_json,
        "booking" : booking_json,

        },

    

    def main():
        """Run the 3 agent healthcare triage system with sample patient complaints."""

        for patient in PATIENT_COMPLAINTS:
            print(f"\n '-' *70")
            print(f"  Patient: {patient['name']} ({patient['patient_id']}, age {patient['age']})")
            print(f"  Complaint: {patient['complaint']}")
            print(f"{'─' * 70}")

            result = run_triage_pipeline(patient)

            print(f"\n  Summary:")
            print(f"    Symptoms found: {result['symptoms'].get('total_matches', '?')}")
            print(f"    Urgency: {result['urgency'].get('urgency', '?')} — {result['urgency'].get('reason', '')}")
            print(f"    Appointment: {result['booking'].get('time_slot', 'N/A')} ({result['booking'].get('status', '?')})")
            print(f"    Instructions: {result['booking'].get('instructions', 'N/A')}")


if __name__ == "__main__":
    main()
                      









