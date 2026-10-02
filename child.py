from strands import Agent,tool
from strands.models import BedrockModel
import json
import datetime
import os 
from utils import _tool_results

AWS_REGION = os.environ.get("AWS_REGION" ,"us-east-1")
MODEL_ID = os.environ.get("MODEL_ID" , "us.anthropic.claude-sonnet-4-5-20250929-v1:0")

PATIENT_COMPLAINTS =[
    {
        "patient_id":"P-1001",
        "name" :"Alice Johnson",
        "complaint" : "I've been having sharp chest pain for the past 2 hours,"
                    "along with shortness of breath and dizziness. ",
        "age" : 58,   
    },
    {
        "patient_id" :"p-1002",
        "name" : "Bob Smith",
        "complaint" :"I have a mild headache and a runny nose that started yesterday. "
                      "No fever.",
        "age": 32,
    },
    {
        "patient_id" : "P-1003",
        "name" : "Carol Davis",
        "complant" : "My ankle is swollen and painful after I twisted it while jogging  "
                      "this morning. I can still put somw weight on it. ",
        "age" : 27,
    },
]

AVAILABLE_SLOTS ={
    "urgent":[ "09:00 AM(Emergency)", "09:15 AM (Emergency)"],
    "standard" : ["10:30 AM" , "11:00 AM","11.30 AM"],
    "routine" :["02:00 PM ", "02:30 PM", "03:00 PM ","03:30 PM"],
}

SYMPTOM_CONDITIONS ={
    "chest_pains" :{"condition" : "Possible cardiac event","severity":"high","keywords":["chest pain","chest"]},
    "shortness of breath":{"condition":"Respiratory distress" , "severity" :"high" ,"keywords":["shortness of breath","breathing","breath"]},
    "dizziness" :{"condition":"Circulatory issue" ,"severity":"medium","keywords":["dizziness","dizzy","lightheaded"]},
    "headache": {"condition":"Tension headache" ,"severity":"low"," keywords":["headache","head pain"]},
    "runny nose":{"condition":"Upper respiratory infection" ,"severity":"low", "keywords" :["running nose","congestion","nasal"]},
    "swollen ankle":{"condition":"Possible sprain","severity":"medium","keywords":["swollen","ankle","twisted","sprain"]}

}

def build_symptom_analyzer() -> Agent:
    """Build the Symptom Analyzer agent with a lookup_symptoms tool."""

    model = BedrockModel(
    model_id = MODEL_ID,
    region_name = AWS_REGION,
    temperature =0.0,)

    @tool
    def lookup_symptoms(complaint_text: str)->str:
        """Parse a patient complaint and match symptoms against the knowledge base.
        Args:
           complaint_text:The raw patient complaint text
        Returns:
        JSON string with matched symptoms,conditions, and severity levels
         """

        complaint_lower = complaint_text.lower()
        matches =[]
        for symptom ,info in SYMPTOM_CONDITIONS.items():
            if any(kw in complaint_lower for kw in info["keywords"]):
                matches.append({
                    "symptom":symptom,
                    "condition":info["condition"],
                    "severity" :info["severity"],
                })
                result = json.dumps({
                    "matched_symptoms":matches,
                    "total_matches":len(matches),
                },indent =2)
                _tool_results["symptoms"] = result
                return result 


    system_prompt ="""You are a Symptom Analyzer agent. Your ONLY job is symptom analysis.
        call the lookup_symptoms tool with the patient's complaint text. 
        After the tool returns,output ONLY the raw JSON result.Do no classify urgency or book appointments."""

    return Agent(
        model = model,
        system_prompt =system_prompt,
        tools =[lookup_symptoms],
         )

def build_urgency_classifier() ->Agent:
    """Build the Urgency Classifier agent with a classify_urgency tool."""

    model = BedrockModel(
        model_id =MODEL_ID,
        region_name = AWS_REGION,
        temperature =0.0,
    )

    @tool 
    def classify_urgency(symptom_json:str) ->str:
        """Classify triage urgency based on symptom analysis results.
        Rules:
        - If ANY severity is "high" -> urgency ="urgent "
        - If Any severity is "medium" (none high) -> urgency ="standard"
        - If all severities are "low" ->urency ="routine"

        Args:
           symptom_json: JSON string from the Symptom Analyzer
        Returns:
           JSON  string with urgency level and reasoning 

        """
        severities = []

        try:
            data = json.loads(symptom_json)
            symptoms = data.get("matched_symptoms",[])
            severities =[s.get("severity","low") for s in symptoms]
        except(json.JSONDecodeError, AttributeError,TypeError):
            text_lower = symptom_json.lower()
            if "high" in text_lower:
                severities.append("high")

            if "medium" in text_lower:
                severities.append("medium")
            if "low" in text_lower:
                severities.append("low")
            if not severities:
                severities.append("low")

        if "high" in severities:
            urgency ="urgent"
            reason ="High-severity symptoms detected -possible cardiac or respiratory disease event"
        elif "medium" in severities:
            urgency ="medium"
            reason ="Medium-severity symptoms detected -requires same day attention"
        else:
            urgency="routine"
            reason="Low-severity symptoms -suitable for routine appointment"

        result= json.dumps({
            "urgency": urgency,
            "reason": reason ,
            "severity_breakdown" :severities,
        }, indent =2 )

        _tool_result["urgency"]= result
        return result

    system_prompt ="""You are an Urgency Classifier agent.Your ONLY job is urgency classification.
    You will receive symptom analysis JSON. Call the classify_urgency too, with that JSON.
    After the tool returns, output ONLY the raw json .Do not anlyze symptoms or book appointments."""

    return Agent(
        model =model,
        system_prompt =system_prompt,
        tools =[classify_urgency],

    )

def build_appointment_scheduler()-> Agent:
    """Build the Appointments Scheduler agent with a book_appointment tool."""
    model = BedrockModel(
         model_id = MODEL_ID,
         region_name = AWS_REGION,
         temperature= 0.0,
     )

    @tool
    def book_appointment(patient_id :str, urgency_levels:str)->str:
        """Book an appointment slot based on urgency level.
        
        Args:
        patient_id : The patient's unique identifier
        urgency_level : One of "urgent" ,"standard", or "routine"

        Returns:
        JSON string with booking confirmation and assigned time slot
        """

        urgency_key = urgency_levels.lower().strip()
        slots = AVAILABLE_SLOTS.get(urgency_key, AVAILABLE_SLOTS["routine"])
        if not slots:
            return json.dumps({
                "status" :"no_availability",
                "message" :f"No {urgency_key} slots available.",

            })
        assigned_slot =slots[0]
        today = datetime.now().strftime("%Y- %M- %d")
        result = json.dumps({
            "status":"booked",
            "patient_id":patient_id,
            "date":today,
            "time_slot":assigned_slot,
            "urgency":urgency_key,
            "instructions":{
                "urgent":"Proceed to emergency intake immeadiately",
                "standards":"Please arrive 13 minutes early for intake.",
                "routine":"Please arrive 10 minutes before year appointment.",
            }.get(urgency_key,"Please arrive on time. ",)
        },indent =2)
        _tool_results["booking"] = result
        return result 

    system_prompt ="""You are an Appointment Scheduler agent. Your ONLY job is booking_appointments.
        You will receive a patient_id and urgency_level.Call the book_appointment tool with those values.
        After the tool returns,output ONLY the raw JSON result.Do not analyze symptoms or classify urgency.
        """
    return Agent(
        model = model,
        system_prompt =system_prompt,
        tools =[book_appointment],
    )


        

