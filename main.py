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
- Any other technical parameters as additional keys.
If unrelated to drilling, return {"type":"irrelevant"}.
"""


@app.post("/sms")
async def reply_to_sms(Body: str = Form(...), From: str = Form(...)):
    print(f"Received message {From}: {Body}")

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

    payload = {
        "sender": From,
        "raw_message": Body,
        "job_id": parsed.get("job_id"),
        "parsed": parsed,
    }

    try:
        res = supabase.table("drill_logs").insert(payload).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    step = parsed.get("step") or "update"
    depth = parsed.get("depth_ft") or "unknown"
    msg = f"Logged {step} at {depth} ft."

    return Response(
        content=f"<Response><Message>{msg}</Message></Response>",
        media_type="application/xml",
    )
