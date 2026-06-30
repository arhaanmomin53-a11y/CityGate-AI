from google.adk.workflow import Workflow, START
from google.adk.agents import LlmAgent
from google.adk.events.event import Event
from google.adk.events.request_input import RequestInput
from google.adk.agents.context import Context
from google.adk.apps import App, ResumabilityConfig

from .schemas import (
    IngestFieldConflict,
    ExtractedConflictSchema,
    ProposedWorkaround
)
from .tools import query_mcp_drawings, validate_clearance

# Node A: Extraction LLM Agent
extract_conflict = LlmAgent(
    model="gemini-flash-latest",
    instruction="""You are an expert heavy industrial RFI information extraction agent. 
    Analyze the subcontractor's voice transcript and extract coordinates and clash details.
    Always output structured schema with level, grid line, clashing trades, and clearance corridor values.""",
    output_schema=ExtractedConflictSchema,
    output_key="extracted_conflict"
)

# Node B: MCP Server Lookup (wrapped in a python function node)
def mcp_lookup(ctx: Context, node_input: dict) -> Event:
    """Node B: Queries the project's external document repository via MCP connection tools."""
    # Retrieve current attempt count from state (defaults to 1)
    attempt = ctx.state.get("mcp_attempt_count", 1)
    
    # Predecessor Node A output is in node_input
    # LlmAgent outputs are dictionary structures when output_schema is set
    level = node_input.get("level", "Level 3")
    grid_line = node_input.get("grid_line", "Grid F-12")
    
    # Query files via mock MCP tool
    drawings_data = query_mcp_drawings(level=level, grid_line=grid_line, attempt=attempt)
    
    return Event(
        output=drawings_data,
        state={"mcp_drawings": drawings_data, "mcp_attempt_count": attempt}
    )

# Node C: Deterministic Validation check
def deterministic_validation(ctx: Context, node_input: dict) -> Event:
    """Node C: Deterministically validates the CAD proposal for clearance corridors."""
    drawings = node_input  # Output from mcp_lookup
    drawing_file = drawings.get("drawing_file", "")
    
    # Retrieve reported clearance from Node A state
    conflict_data = ctx.state.get("extracted_conflict", {})
    reported_clearance = conflict_data.get("reported_clearance_inches", 8.5)
    
    # Run mathematical check for minimum 18-inch corridor clearance
    validation = validate_clearance(drawing_file, reported_clearance)
    math_passed = validation.get("math_check_passed", False)
    
    if not math_passed:
        # Route back to Node B to search for alternate revisions, incrementing attempt
        current_attempt = ctx.state.get("mcp_attempt_count", 1)
        return Event(
            output=validation,
            route="retry",
            state={"mcp_attempt_count": current_attempt + 1}
        )
    else:
        # Validation passed, route to HITL Pause Gate
        return Event(
            output=validation,
            route="hitl",
            state={"validation_details": validation}
        )

# Human-In-The-Loop Pause Node
async def awaiting_human_validation(ctx: Context, node_input: dict):
    """Pause execution state until human validation token is provided by Stitch frontend."""
    if not ctx.resume_inputs:
        # Freeze memory and serialize parameters into a payload
        payload = {
            "ticket_id": ctx.state.get("extracted_conflict", {}).get("ticket_id"),
            "resolved_clearance": node_input.get("resulting_clearance_inches"),
            "drawing_target": ctx.state.get("mcp_drawings", {}).get("drawing_file"),
            "validation": "PASSED"
        }
        # Yield RequestInput to trigger app-level HITL pause
        yield RequestInput(
            interrupt_id="hitl_approval_gate",
            message=f"HITL Pause. Serialized State Payload: {payload}"
        )
        return
        
    # Resume execution has occurred! Retrieve human token
    token = ctx.resume_inputs.get("hitl_approval_gate")
    
    # Expected format: HITL-GATE-[NumericTicketId]
    ticket_raw = ctx.state.get("extracted_conflict", {}).get("ticket_id", "RFI-402")
    # Extract numbers from ticket ID (e.g. RFI #402 -> 402)
    import re
    nums = re.findall(r'\d+', ticket_raw)
    num_suffix = nums[0] if nums else "402"
    expected_token = f"HITL-GATE-{num_suffix}"
    
    if token != expected_token:
        # Throw validation error or re-request token
        yield RequestInput(
            interrupt_id="hitl_approval_gate",
            message=f"SECURITY VIOLATION: Invalid approval token '{token}'. Expected '{expected_token}'."
        )
        return
        
    yield Event(
        output={"token_verified": True, "token": token},
        state={"hitl_approved": True}
    )

# Node E: Commit to Master ERP
def commit_to_erp(ctx: Context, node_input: dict) -> ProposedWorkaround:
    """Node E: Drafts the workaround proposal. Staged for commit without database write access."""
    conflict = ctx.state.get("extracted_conflict", {})
    drawings = ctx.state.get("mcp_drawings", {})
    validation = ctx.state.get("validation_details", {})
    
    # Master CAD database direct modification block (Anti-hallucination safety guardrail)
    # Staging as a draft proposal model
    proposal = ProposedWorkaround(
        ticket_id=conflict.get("ticket_id", "RFI #402"),
        clash_resolved=f"{' vs '.join(conflict.get('clashing_trades', []))}",
        drawing_target=drawings.get("drawing_file", ""),
        resolution_action="Reroute plumbing sleeve and adjust HVAC brackets.",
        resulting_clearance_inches=validation.get("resulting_clearance_inches", 22.0),
        validation_status="Staged to ERP (Draft Proposal - Committed by HITL Approval)"
    )
    return proposal

# Assemble Workflow Graph using ADK 2.0 primitives
rfi_resolution_graph = Workflow(
    input_schema=IngestFieldConflict,
    output_schema=ProposedWorkaround,
    edges=[
        ('START', extract_conflict),
        (extract_conflict, mcp_lookup),
        (mcp_lookup, deterministic_validation),
        # Node C validation loop
        (deterministic_validation, mcp_lookup, "retry"),
        # Node C validation passed route
        (deterministic_validation, awaiting_human_validation, "hitl"),
        # HITL pause passed route
        (awaiting_human_validation, commit_to_erp)
    ]
)

# Container Application with Resumability enabled for Human-in-the-Loop state persists
app = App(
    root_agent=rfi_resolution_graph,
    resumability_config=ResumabilityConfig(is_resumable=True)
)
