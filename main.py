import os
import json
from fastapi import FASTAPI, Form, Response
from supabase import create_client, Client
from openai import OpenAI

app = FastAPI()

supabase: Client = create_client(
    os.environ.get("SUPABASE_URL"),
    os.environ.get("SUPABASE_KEY")
)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

SYSTEM_PROMPT = """
You are a geothermal data parser. Your job is to extract technical drilling data from unstructured text messages. Output ONLY valid JSON.
-Identify the job_if if present (look for patterns like GEO-123). If not found, return NULL. 
-Extract 'depth' in feet, 'step' (e.g. Casing, Rod, Grouting), and 'status' (Start, Stop, In Progress).
-Extract ANY other technical parameters (mud weight, flow rate, ground conditions) as their own keys
-If the text is unrelated to work, return {"type": "irrelevant"}
"""

@app.post("/sms")
async def reply_to_sms(Body: str = Form(...), From: str = Form(...)):
        print(f"Received message {From}: {Body}")

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": Body}
        ],
        temperature=0
    )

    parsed_data = json.load(completion.choices[0].messages.content)

    data_payload = {
        "job_id": parsed_data.get("job_id", "UNKNOWN"),
        "raw_message": Body,
        "drill_data": parsed_data
    }
    supabase.table("drill_logs".insert(data_payload).execute

    response_msg = f"Copy. Logged {parsed_data.get('step', 'update')} at {passed_data.get('depth', 'unknown')} ft."
    return Response(content=f"<Response><Message>{response_msg}</Message></Response>", media_type = application/xml")