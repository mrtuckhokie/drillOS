import os
import json
from fastapi import FastAPI, Form, Response, HTTPException
from supabase import create_client, Client
from openai import OpenAI

app = FastAPI()

supabase: Client = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_KEY"],
)

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

SYSTEM_PROMPT = """
You extract geothermal drilling data from unstructured field messages.
Return ONLY strict JSON.

Fields:
- job_id: pattern GEO-### if present, else null.
- depth_ft: numeric if mentioned.
- step: e.g. "casing", "rod", "grouting".
- status: start / stop / in_progress.
- mud_weight: numeric if present
- flow_rate: numeric if present
- ground_conditions: text if present
If unrelated to drilling, return {"type":"irrelevant"}.
"""


@app.post("/sms")
async def reply_to_sms(Body: str = Form(...), From: str = Form(...)):
    print(f"Received message {From}: {Body}")

    # Call OpenAI to parse message
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": Body},
        ],
        temperature=0,
    )

    raw = completion.choices[0].message.content

    try:
        parsed = json.loads(raw)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid JSON returned from model")

    # If message is irrelevant, skip logging
    if parsed.get("type") == "irrelevant":
        return Response(
            content=f"<Response><Message>Message ignored, not relevant to drilling.</Message></Response>",
            media_type="application/xml",
        )

    # Map parsed fields into dedicated table columns
    payload = {
        "job_id": parsed.get("job_id"),
        "raw_message": Body,
        "step": parsed.get("step"),
        "status": parsed.get("status"),
        "depth_ft": parsed.get("depth_ft"),
        "mud_weight": parsed.get("mud_weight"),
        "flow_rate": parsed.get("flow_rate"),
        "ground_conditions": parsed.get("ground_conditions"),
        "drill_data": parsed,  # full JSON backup
    }

    try:
        supabase.table("drill_logs").insert(payload).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    step = payload.get("step") or "update"
    depth = payload.get("depth_ft") or "unknown"
    msg = f"Logged {step} at {depth} ft."

    return Response(
        content=f"<Response><Message>{msg}</Message></Response>",
        media_type="application/xml",
    )
