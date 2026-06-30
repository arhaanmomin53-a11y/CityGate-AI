"""Pipeline orchestrator — runs agents in sequence with status tracking."""
import uuid
from typing import Optional

from backend.agents.intake_coordinator import process_intake
from backend.agents.document_parser import parse_document
from backend.agents.compliance_engine import analyze_compliance
from backend.agents.advocacy_agent import register_license
from backend.mcp.city_code_server import mcp_fetch_city_code, mcp_verify_permit_status
from backend.skills.form_filler import build_form_comparison, fill_pdf_form
from backend.skills.pii_vault import get_vault_stats

PIPELINE_STAGES = [
    {"id": "intake", "label": "Processing Intake", "color": "yellow", "agent": "intake_coordinator"},
    {"id": "vault", "label": "Vaulting PII", "color": "yellow", "agent": "pii_vault"},
    {"id": "parse", "label": "Parsing Photo", "color": "yellow", "agent": "document_parser"},
    {"id": "city_code", "label": "Looking Up City Code", "color": "blue", "agent": "mcp"},
    {"id": "compliance", "label": "Reviewing Legal Terms", "color": "blue", "agent": "compliance_engine"},
    {"id": "form_fill", "label": "Preparing Form", "color": "blue", "agent": "form_filler"},
    {"id": "hitl", "label": "Awaiting Human Approval", "color": "orange", "agent": "hitl"},
    {"id": "complete", "label": "Complete", "color": "green", "agent": "done"},
]

SESSIONS: dict[str, dict] = {}


def create_session(text: str, image_source: str = "business_license", language: Optional[str] = None) -> dict:
    session_id = str(uuid.uuid4())
    token = f"HITL-GATE-{session_id[:8].upper()}"

    SESSIONS[session_id] = {
        "session_id": session_id,
        "status": "running",
        "current_stage": "intake",
        "stages_completed": [],
        "token": token,
        "input": {"text": text, "image_source": image_source, "language": language},
        "results": {},
        "approved": False,
    }
    return SESSIONS[session_id]


def get_session(session_id: str) -> Optional[dict]:
    return SESSIONS.get(session_id)


def run_pipeline(session_id: str) -> dict:
    session = SESSIONS.get(session_id)
    if not session:
        return {"error": "Session not found"}

    text = session["input"]["text"]
    image = session["input"]["image_source"]
    lang = session["input"].get("language")

    intake = process_intake(text, lang)
    session["stages_completed"].append("intake")
    session["current_stage"] = "vault"
    session["results"]["intake"] = intake

    session["stages_completed"].append("vault")
    session["current_stage"] = "parse"

    parsed = parse_document(image, text)
    session["results"]["document"] = parsed
    session["stages_completed"].append("parse")
    session["current_stage"] = "city_code"

    zip_code = intake.get("extracted_fields", {}).get("zip_code") or "78205"
    for f in parsed.get("fields", []):
        if f.get("field_id") == "zip_code" and f.get("value"):
            zip_code = f["value"]

    city_code = mcp_fetch_city_code(zip_code, parsed.get("form_type"))
    session["results"]["city_code"] = city_code
    session["stages_completed"].append("city_code")
    session["current_stage"] = "compliance"

    compliance = analyze_compliance(parsed, intake, city_code)
    session["results"]["compliance"] = compliance
    session["stages_completed"].append("compliance")
    session["current_stage"] = "form_fill"

    comparison = build_form_comparison(
        parsed.get("fields", []),
        intake,
        parsed.get("form_type", "business_license"),
    )
    session["results"]["form_comparison"] = comparison
    session["stages_completed"].append("form_fill")
    session["current_stage"] = "hitl"
    session["status"] = "awaiting_approval"

    return session


def approve_and_submit(session_id: str, token: str) -> dict:
    session = SESSIONS.get(session_id)
    if not session:
        return {"error": "Session not found"}
    if token != session["token"]:
        return {"error": "Invalid security token", "status": "denied"}

    comparison = session["results"].get("form_comparison", {})
    fill_result = fill_pdf_form(comparison, approved=True)
    session["results"]["submission"] = fill_result
    session["approved"] = True
    session["status"] = "submitted"
    session["current_stage"] = "complete"
    session["stages_completed"].append("hitl")
    session["stages_completed"].append("complete")

    intake = session["results"].get("intake", {})
    business_name = intake.get("extracted_fields", {}).get("business_name", "Unknown Business")
    register_license(business_name, "Business License")

    permit_status = mcp_verify_permit_status("pending")
    session["results"]["permit_status"] = permit_status

    return session


def get_agent_status(session_id: str) -> dict:
    session = SESSIONS.get(session_id)
    if not session:
        return {"stages": PIPELINE_STAGES, "current": None}

    current = session.get("current_stage", "intake")
    completed = set(session.get("stages_completed", []))

    stages = []
    for s in PIPELINE_STAGES:
        stage = dict(s)
        if s["id"] in completed:
            stage["state"] = "completed"
        elif s["id"] == current:
            stage["state"] = "active"
        else:
            stage["state"] = "pending"
        stages.append(stage)

    return {"stages": stages, "current": current, "session_status": session.get("status")}
