from pydantic import BaseModel, Field
from typing import List

class IngestFieldConflict(BaseModel):
    """Entry schema for a subcontractor-reported physical obstruction on site."""
    ticket_id: str = Field(description="Unique identifier for the RFI, e.g. RFI #402")
    text_description: str = Field(description="Voice-to-text transcription of conflict reported by subcontractor")
    image_url: str = Field(description="URL or path to the photograph of physical on-site obstruction")

class ExtractedConflictSchema(BaseModel):
    """Structured data extracted from the unstructured subcontractor report (Node A)."""
    ticket_id: str = Field(description="Unique RFI ticket ID")
    grid_line: str = Field(description="Grid line coordinate of the conflict (e.g. Grid F-12)")
    level: str = Field(description="Building level coordinate of the conflict (e.g. Level 3)")
    clashing_trades: List[str] = Field(description="Trades involved in the physical clash (e.g. HVAC, Plumbing)")
    reported_clearance_inches: float = Field(description="Estimated clearance corridor currently available")
    required_clearance_inches: float = Field(default=18.0, description="Required minimum clearance corridor (typically 18 inches)")

class ProposedWorkaround(BaseModel):
    """Agent's drafted workaround proposal staged for ERP commit (Node C / HITL Gate)."""
    ticket_id: str = Field(description="Reference RFI ticket ID")
    clash_resolved: str = Field(description="Summary of the resolved collision")
    drawing_target: str = Field(description="Exact drawing file reference string retrieved from MCP")
    resolution_action: str = Field(description="Specific workaround actions drafted for the trade crews")
    resulting_clearance_inches: float = Field(description="Clearance corridor achieved by this workaround")
    validation_status: str = Field(description="Validation state (e.g. Spatial Check Passed)")
