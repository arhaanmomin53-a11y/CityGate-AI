# Architectural Implementation Blueprint: Site Clash AI Gatekeeper

This document establishes the comprehensive architectural blueprint and design specification for the **Site Clash AI Gatekeeper** developed during the Kaggle 5-Day AI Agents Intensive. This blueprint details the integration between a high-fidelity, futuristic HUD frontend dashboard and a graph-based agent backend using the Antigravity IDE and Agent Development Kit (ADK 2.0).

---

## 1. System Architecture Overview

The system bridges unstructured subcontractor field reports with deterministic B2B architectural databases. The architecture is split into a client-side HUD presentation layer and an agentic graph execution layer.

```mermaid
graph TD
    subgraph Client Presentation (Futuristic HUD UI)
        Form[Report New Site Conflict Form] -->|1. Submit Input| Queue[Active Conflict Feed]
        Queue -->|2. Selection / Load Plan| Viewport[Laser-Scanning Viewport]
        Tabs[Tabbed Workspace] -->|3. View Database Logs| Viewport
        GovBar[Governance Footer] -->|4. Input Security Token & Confirm| MasterDB[Master Site Plan Database]
    end

    subgraph Agent Graph Execution (ADK 2.0 Workflow)
        START --> NodeA[Node A: ExtractConflict]
        NodeA -->|Structured Details| NodeB[Node B: MCPLookup]
        NodeB -->|Load CAD Drawings| NodeC[Node C: DeterministicValidation]
        NodeC -->|Validation Failed: Clearance < 18\"| NodeB
        NodeC -->|Validation Passed: Clearance >= 18\"| NodeD[Node D: AwaitingHumanValidation]
        NodeD -->|Persisted Pause / RequestInput| WaitState((HITL Security Gate))
        WaitState -->|Token Verified| NodeE[Node E: CommitToERP]
    end

    ClientPresentation -.- AgentGraphExecution
    Viewport -.->|Visual Overlay Highlights| NodeB
    WaitState -.->|Await Security Code Input| GovBar
    NodeE -.->|Staged Draft Proposal| MasterDB
```

---

## 2. Futuristic HUD Frontend Specification

The dashboard is developed as a responsive single-page web application featuring high-fidelity, cyberpunk-inspired Heads-Up Display (HUD) styles.

### Color & Aesthetic Token Palette
*   **Background Canvas**: Deep Obsidian Black (`#06060a`)
*   **Active Processes & Scan**: Electric Neon Cyan (`#00F0FF`)
*   **Exceptions & Alerts**: Neon Warning Orange (`#FF5E00`)
*   **Passed Validation / Confirmation**: Neon Emerald Green (`#00FF66`)
*   **Clash Bounding Box (HVAC)**: Translucent Crimson (`rgba(255, 0, 85, 0.15)`)
*   **Clash Bounding Box (Plumbing)**: Translucent Amber (`rgba(255, 94, 0, 0.15)`)

### Panel Layout Architecture
1.  **Issue Control Panel (Left 25% Width)**: 
    *   **Submit Form**: Allows on-site crews to report physical conflicts. Users can choose reporting trade, type voice text, select mock photos, or load preset scenario templates.
    *   **Active Conflict Feed**: Starts with no sample data. Dynamically list ingested issues. Statuses change from `Running Scan` to `Review Required` and `Committed`.
2.  **AI Decision Resolution Engine Panel (Center 75% Width)**:
    *   **Left Half (Laser-Scanning Viewport)**: A CAD coordinate viewer drawing overlapping bounding boxes and clearance measure lines, complete with a laser scanning beam overlay.
    *   **Right Half (Tabbed Workspace)**: Displays Parsed Problem Details, live Blueprint Database Search Logs, and Markdown-rendered Suggested Resolution Plans.
3.  **Governance Command Bar (Bottom Footer 100% Width)**: Persistent validation panel containing checklist items (Physical Clearance Check, AI Decision Validation) and Action buttons (Route to Human Engineer, Confirm & Deploy to Master Blueprints).

### UX Interaction Flow
*   **Progressive Disclosure**: Click selection updates CAD viewports and tabs. Search logs remain hidden under Tab 2 unless clicked.
*   **System Status Shimmers**: A scanning laser line sweeps down the CAD blueprint during calculations. The "CONFIRM" button is locked until checks return `PASSED`.
*   **Success Animation**: On confirmation, the card morphs and slides out to the right, resetting the workspace panels back to empty/idle state.

---

## 3. Agent Backend Specification (ADK 2.0)

The underlying processing layer is implemented using `google.adk.workflow` graph routing primitives.

### Graph Flow Primitives
*   **Input Data Model**: [IngestFieldConflict](file:///c:/Users/ACER/OneDrive/Desktop/NEW%20CAP%20STONE%20PROJECT/rfi_agent/schemas.py#L3-L7) - types incoming data into `ticket_id`, `text_description`, and `image_url`.
*   **Node A (Extraction)**: [ExtractConflict](file:///c:/Users/ACER/OneDrive/Desktop/NEW%20CAP%20STONE%20PROJECT/rfi_agent/agent.py#L11-L20) - LlmAgent using the core language model to transform unstructured text into structured schema variables ([ExtractedConflictSchema](file:///c:/Users/ACER/OneDrive/Desktop/NEW%20CAP%20STONE%20PROJECT/rfi_agent/schemas.py#L9-L16)).
*   **Node B (MCP Lookup)**: [mcp_lookup](file:///c:/Users/ACER/OneDrive/Desktop/NEW%20CAP%20STONE%20PROJECT/rfi_agent/agent.py#L22-L38) - Python function node that invokes the MCP toolsets to query drawings matching grid lines and level references.
*   **Node C (Deterministic Validation)**: [deterministic_validation](file:///c:/Users/ACER/OneDrive/Desktop/NEW%20CAP%20STONE%20PROJECT/rfi_agent/agent.py#L40-L64) - Math solver evaluating physical clearances. If resulting clearance is `< 18"` (e.g. 8.5"), the node emits an `Event` with `route="retry"`, cycling back to Node B to query alternative drawing revisions. If resulting clearance is `>= 18"`, the node routes to `awaiting_human_validation` via `route="hitl"`.

---

## 4. Core Enterprise Security Features

1.  **Anti-Hallucination Guardrails**: The agent is structurally banned from modifying the master project CAD database directly. Workarounds are generated as draft models ([ProposedWorkaround](file:///c:/Users/ACER/OneDrive/Desktop/NEW%20CAP%20STONE%20PROJECT/rfi_agent/schemas.py#L18-L26)), which are committed only as staged data.
2.  **Human-In-The-Loop (HITL) State Pause**: If validation succeeds, Node D ([awaiting_human_validation](file:///c:/Users/ACER/OneDrive/Desktop/NEW%20CAP%20STONE%20PROJECT/rfi_agent/agent.py#L66-L101)) yields a `RequestInput` with the serialized state payload, pausing execution until a valid approval token (e.g. `HITL-GATE-1`) is sent via the Stitch UI.
3.  **Sensitive Credential Masking**: A static pre-compilation script ([lint_security.py](file:///c:/Users/ACER/OneDrive/Desktop/NEW%20CAP%20STONE%20PROJECT/lint_security.py)) scans files for secrets. Any detection triggers a `SecurityViolationException` and instantly terminates execution.

---

## 5. File Registry Map
*   **Frontend UI Structure**: [index.html](file:///c:/Users/ACER/OneDrive/Desktop/NEW%20CAP%20STONE%20PROJECT/index.html)
*   **Stitch HUD Style Definitions**: [index.css](file:///c:/Users/ACER/OneDrive/Desktop/NEW%20CAP%20STONE%20PROJECT/index.css)
*   **HUD Interaction & Simulation**: [app.js](file:///c:/Users/ACER/OneDrive/Desktop/NEW%20CAP%20STONE%20PROJECT/app.js)
*   **ADK 2.0 Graph Workflow**: [agent.py](file:///c:/Users/ACER/OneDrive/Desktop/NEW%20CAP%20STONE%20PROJECT/rfi_agent/agent.py)
*   **Mock Database & Math Tools**: [tools.py](file:///c:/Users/ACER/OneDrive/Desktop/NEW%20CAP%20STONE%20PROJECT/rfi_agent/tools.py)
*   **Structured Schemas**: [schemas.py](file:///c:/Users/ACER/OneDrive/Desktop/NEW%20CAP%20STONE%20PROJECT/rfi_agent/schemas.py)
*   **Security Static Analyzer**: [lint_security.py](file:///c:/Users/ACER/OneDrive/Desktop/NEW%20CAP%20STONE%20PROJECT/lint_security.py)
