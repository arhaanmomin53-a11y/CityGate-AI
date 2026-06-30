from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.orchestrator import (
    create_session, get_session, run_pipeline, approve_and_submit, get_agent_status, PIPELINE_STAGES,
)
from backend.agents.advocacy_agent import get_license_memory, run_proactive_check
from backend.agents.intake_coordinator import PRESET_INTAKES, process_intake
from backend.mcp.city_code_server import mcp_fetch_city_code, mcp_verify_permit_status, MCP_TOOLS
from backend.skills.pii_vault import get_vault_stats, vault_text
from backend.skills.ocr_engine import get_form_mapping_schema
from backend.skills.secure_alerts import get_alerts
from backend.security_audit import run_full_audit, log_hitl_approval

app = FastAPI(title="CityGate — Municipal Compliance Platform", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class IntakeRequest(BaseModel):
    text: str
    image_source: str = "business_license"
    language: str | None = None


class ApproveRequest(BaseModel):
    token: str


class CityCodeRequest(BaseModel):
    zip_code: str
    form_type: str | None = None

@app.get("/api/health")
async def health():
    return {"status": "ok", "platform": "CityGate", "version": "1.0.0"}


@app.get("/api/pipeline/stages")
async def pipeline_stages():
    return {"stages": PIPELINE_STAGES}


@app.get("/api/presets")
async def presets():
    return PRESET_INTAKES


@app.post("/api/intake")
async def intake_only(payload: IntakeRequest):
    result = process_intake(payload.text, payload.language)
    return JSONResponse(result)


@app.post("/api/session")
async def create_and_run(payload: IntakeRequest):
    session = create_session(payload.text, payload.image_source, payload.language)
    run_pipeline(session["session_id"])
    return JSONResponse(get_session(session["session_id"]))


@app.get("/api/session/{session_id}")
async def get_session_data(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return JSONResponse(session)


@app.get("/api/session/{session_id}/status")
async def session_status(session_id: str):
    return JSONResponse(get_agent_status(session_id))


@app.post("/api/session/{session_id}/approve")
async def approve_session(session_id: str, payload: ApproveRequest):
    result = approve_and_submit(session_id, payload.token)
    if result.get("error"):
        log_hitl_approval(session_id, False, False)
        raise HTTPException(status_code=400, detail=result["error"])
    log_hitl_approval(session_id, True, True)
    return JSONResponse(result)


@app.post("/api/mcp/city-code")
async def city_code_lookup(payload: CityCodeRequest):
    return JSONResponse(mcp_fetch_city_code(payload.zip_code, payload.form_type))


@app.get("/api/mcp/permit-status/{permit_id}")
async def permit_status(permit_id: str):
    return JSONResponse(mcp_verify_permit_status(permit_id))


@app.get("/api/mcp/tools")
async def mcp_tools():
    return {"tools": MCP_TOOLS}


@app.get("/api/vault/stats")
async def vault_stats():
    return JSONResponse(get_vault_stats())


@app.get("/api/schema/form-mapping")
async def form_schema():
    return JSONResponse(get_form_mapping_schema())


@app.get("/api/advocacy/licenses")
async def licenses(business_id: str | None = None):
    return JSONResponse(get_license_memory(business_id))


@app.post("/api/advocacy/check-renewals")
async def check_renewals(business_id: str | None = None):
    return JSONResponse(run_proactive_check(business_id))


@app.get("/api/alerts")
async def alerts(unread_only: bool = False):
    return JSONResponse({"alerts": get_alerts(unread_only=unread_only)})


@app.get("/api/security/audit")
async def security_audit():
    return JSONResponse(run_full_audit())


frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="static")
