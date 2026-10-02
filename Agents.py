from strands import Agent,tool
from healthcare import MODEL_ID,AWS_REGION
from strands.model import BedrockModel


PATIENT_COMPLAINTS =[
    {
        "patient_id":"P-1001",
        "nane" :"Alice Johnson",
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
