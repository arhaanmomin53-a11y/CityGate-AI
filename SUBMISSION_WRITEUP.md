# CityGate — Devpost / Hackathon Submission Write-Up

Copy each section below into the corresponding field on your submission platform.

---

## Title *(Required)*

**CityGate**

---

## Subtitle

**The AI municipal gateway that vaults your data, checks city code, and won't file until you approve.**

---

## Card and Thumbnail Image

**What to upload:** A 1600×900 or 1280×720 screenshot of the CityGate dashboard showing:
- The **CityGate** logo in the navbar
- The **agent pipeline tracker** (Processing Intake → … → Complete)
- The **Three.js 3D city view** with buildings lit up
- A permit card in the queue

**How to capture:**
1. Run the app at `http://127.0.0.1:8000`
2. Start a permit with the English preset
3. Screenshot when the 3D view is active (before or after HITL modal)
4. Crop to 16:9 ratio

**Suggested caption for thumbnail:** *"CityGate — multilingual permit intake with human-in-the-loop filing"*

---

## Submission Tracks

Select tracks that fit your hackathon. Recommended:

- **AI / Machine Learning** — multi-agent NLP pipeline
- **Social Good / Civic Tech** — municipal compliance for small businesses
- **Best Use of MCP** — Model Context Protocol city-code tools
- **Best UI/UX** — Three.js reactive dashboard + HITL modal
- **Security / Privacy** — local PII vaulting

---

## Images *(Media Gallery)*

Upload 3–5 screenshots:

| # | What to show | Caption |
|---|--------------|---------|
| 1 | Full dashboard — queue + 3D view + agent tracker | Main CityGate command center |
| 2 | HITL modal — side-by-side form comparison | Human approval checkpoint — no auto-submit |
| 3 | Multilingual intake modal (Español preset) | Supports English, Spanish, Vietnamese, Arabic |
| 4 | Advocacy tab — license lifecycle + secure alerts | Proactive renewal reminders without PII leaks |
| 5 | Compliance analysis panel with city code results | MCP-powered San Antonio ordinance lookup |

---

## Video *(Optional but recommended — 2–3 min)*

**Script outline:**

1. **0:00–0:20** — Problem: small business owners struggle with confusing municipal forms
2. **0:20–0:45** — Demo: load Spanish preset → start pipeline
3. **0:45–1:30** — Show agent tracker + 3D city reacting to each stage
4. **1:30–2:00** — HITL modal: review fields, enter code, Approve & File
5. **2:00–2:30** — Advocacy tab + security audit (PII vault, no leaked data)
6. **2:30–3:00** — Closing: "CityGate — your data stays local until you say go"

**Recording tip:** Use OBS or Windows Game Bar (`Win + G`), record at 1080p.

---

## Project Description *(Main write-up — paste this)*

### Inspiration

Small business owners — especially non-English speakers — face a maze of municipal permit forms, obscure city codes, and sensitive data requests. One mistake can delay opening by weeks. We built **CityGate** to be the gateway between everyday language and official paperwork, with security and human control at every step.

### What it does

CityGate is a multi-agent municipal compliance platform:

1. **Intake Coordinator** accepts voice or text in English, Spanish, Vietnamese, or Arabic and extracts structured permit fields.
2. **PII Vault** encrypts tax IDs and phone numbers locally, replacing them with tokens before any external processing.
3. **Document Parser** runs OCR and layout analysis on photos of municipal notices or PDF forms.
4. **MCP City Code Server** looks up ordinances and fees by ZIP code (e.g., San Antonio business license requirements).
5. **Compliance Engine** scores your application against applicable regulations and flags gaps.
6. **Form Filler** drafts the official permit application from verified JSON data.
7. **HITL Checkpoint** shows a side-by-side comparison — *What the Form Asks* vs *What the Agent Filled In* — and **nothing submits until you click Approve & File**.
8. **Advocacy Agent** tracks license lifecycles and sends PII-safe renewal alerts weeks before expiry.

The dashboard includes a **reactive Three.js 3D city** where each agent stage lights up a building — drag to orbit, click to inspect, watch the scan plane sweep during processing.

### How we built it

- **Frontend:** HTML/CSS/JS with Three.js (OrbitControls, raycasting, stage-reactive materials)
- **Backend:** Python FastAPI + custom agent orchestrator
- **Skills:** Modular `.skills/` packages for PII vaulting, OCR, form filling, secure alerts
- **MCP:** `mcp_fetch_city_code` and `mcp_verify_permit_status` tools
- **Security:** Fernet-encrypted SQLite vault, HITL audit log, static credential linter

### Challenges we ran into

- Balancing **automation vs. trust** — solved with a mandatory human checkpoint and visible side-by-side review
- **PII handling** — sensitive fields never leave the machine unencrypted; tokens flow through the agent pipeline instead
- **Multilingual extraction** — regex + language detection for colloquial input across four languages
- **Reactive 3D UX** — syncing Three.js scene state to async agent pipeline stages in real time

### Accomplishments that we're proud of

- End-to-end pipeline from natural language → vaulted data → city code → compliance score → human-approved filing
- 100/100 security audit score on vault integrity and HITL gate design
- Interactive 3D visualization that makes abstract agent orchestration tangible
- Built for low-literacy and non-English-speaking business owners (Alt+L large-text mode, multilingual presets)

### What we learned

Agent systems for government workflows need **human gates**, not just smarter automation. Local-first PII vaulting and MCP for external lookups keep credentials out of agent logic while still enabling rich compliance checks.

### What's next for CityGate

- Real Tesseract/EasyOCR integration for on-device document parsing
- Live municipal API connections (replacing mock city-code DB)
- Mobile voice intake with on-device transcription
- SMS/email secure alerts via Twilio with header sanitization
- Usability testing with immigrant-owned businesses in San Antonio

---

## Project Links

| Link | URL |
|------|-----|
| **GitHub Repository** | `https://github.com/YOUR_USERNAME/citygate` |
| **Live Demo** | `http://127.0.0.1:8000` *(local — add deployed URL if hosted)* |
| **API Docs** | `http://127.0.0.1:8000/docs` *(FastAPI Swagger)* |

Replace `YOUR_USERNAME` with your GitHub username after uploading.

---

## Built With (tags)

`python` · `fastapi` · `threejs` · `javascript` · `ai-agents` · `mcp` · `civic-tech` · `security` · `multilingual` · `human-in-the-loop`

---

## Team

*[Add your name(s) and role(s) here]*

Example:
- **Your Name** — Full-stack, agent architecture, UI/UX
