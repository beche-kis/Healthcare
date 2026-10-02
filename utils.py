import time 
import re 

def clean_response(text:str) ->str:
    """Strip claude thinking tags from agent responses ."""
    cleaned = re.sub(r'<thinking>.*?</thinking>','',str(text),
    flags = re.DOTALL)
    return cleaned.strip()

_tool_results ={}


def run_agent_with_retry(agent_builder, prompt: str, max_retries: int= 3) -> str:
    """Runs an agent with retry logic for transient Bedrock errors.
    Uses exponential backoff (1s,2s.3s) to handle throtting."""

    for attempt in range(max_retries):
        try:

            agent = agent_builder()
            result = agent(prompt)
            return clean_response(result)
        except Exception as e:
            if attempt <max_retries - 1:
                wait = 2 **attempt
                print(f"  [Retry {attempt + 1} /{max_retries}]{e.__class__.name__}, waiting{wait}s...")
                time.sleep(wait)
            else:
                print(f"[Failed]{e.__class__.__name__} after {max_retries} attempts")
                raise
            

