# BreatheWise — GenAI Urban Air Quality Assistant

- **Chosen Vertical**: **Climate, Environment & Urban Sustainability — Urban Air Quality Assistant (PromptWars Challenge 06)**
- **Target Persona**: Urban households (families with children, seniors, or respiratory sensitivities) and city commuters navigating severe smog episodes.

BreatheWise helps families and urban communities navigate severe winter smog and air pollution by connecting **transparent, provenance-tagged air quality data** to **personalized exposure & emission routines**, **deterministic indoor air quality sizing**, **quantified sustainability tracking**, **cited AI guidance**, and **moderated community insights**.

---

## 1. Problem, Chosen Vertical, Approach & How the Solution Works

### The Problem
During severe winter smog episodes, families see alarming AQI headlines without clear, trustworthy guidance on:
- Which AQI scale applies (**Indian CPCB NAQI** vs **US EPA AQI** differ significantly at the same `PM2.5` concentration).
- Whether displayed numbers come from **physical ground monitors**, **atmospheric models**, **forecasts**, or **demo snapshots**.
- How to reduce **personal inhalation exposure** (HEPA CADR sizing, indoor clean rooms, inversion-aware timing) versus **community tailpipe/combustion emissions** (`kg CO2e` and `g PM2.5` avoided).

### Approach & Decision Logic
BreatheWise separates responsibilities strictly between **deterministic environmental science** and **bounded GenAI reasoning**:
1. **Context-Driven Decision Making**: Every request binds live city pollutant conditions (`measured` CPCB station data when available in India, otherwise Open-Meteo atmospheric modeling + hourly forecast) with the household profile (children/seniors/sensitivity flags, home type, cooking fuel, HEPA ownership, daily commute mode/distance, and budget tier).
2. **Zero LLM Math**: AQI breakpoints (`Indian NAQI` and `US EPA 2024`), HEPA `CADR`/`ACH` sizing, indoor risk scoring (`0–100`), and commute emission savings (`kg CO2e` and `g PM2.5` avoided) are computed exclusively in deterministic Python services (`aqi_indian.py`, `aqi_us_epa.py`, `iaq_calculator.py`, `sustainability_calculator.py`).
3. **Grounded RAG + Guardrails**: A 6-node **LangGraph** workflow (`load_profile` → `fetch_aqi_context` → `analyze_conditions` → `retrieve_knowledge` → `generate_recommendations` → `validate_recommendations`) retrieves curated WHO/CPCB/US EPA/ASHRAE guidance via Qdrant hybrid RRF search, enforces structured Pydantic schemas with Gemini, strips hallucinated `doc_id` citations, blocks unsupported medical claims, redacts sensitive health labels from prompts, and falls back to `deterministic_fallback` seamlessly if Gemini is unavailable.

### How the Solution Works (7 Core Modules)
1. **Air Quality Dashboard**: Dual-scale gauge (`Indian CPCB NAQI` + `US EPA 2024 AQI`) computed independently, 6 pollutant cards with WHO 2021 ratios, 24h Recharts trajectory, and strict 4-state provenance (`measured`, `modeled_current`, `forecast`, `demo`).
2. **Personalized AI Recommendations**: LangGraph + Qdrant hybrid RAG pipeline (`WHO`, `CPCB GRAP I–IV`, `US EPA`, `ASHRAE 241`) paired with deterministic commute swaps—separating *exposure reduction* from *emissions reduction*.
3. **Indoor Air Quality Advisor**: Deterministic room volume, target ACH (`3.0–6.0 ACH`), required HEPA CADR (`m³/h` & `CFM`), indoor risk score (`0–100`), ventilation windows, and explicit scope notice (*filtration reduces indoor exposure only, never outdoor AQI*).
4. **Smart Daily Routine Planner**: Hourly daily schedule aligned to modeled lowest-exposure hours and inversion peaks, with explicit forecast-uncertainty caveats (never guarantees a forecast window is safe).
5. **Sustainability Impact Tracker**: Persisted daily/weekly/monthly/all-time tracking of `kg CO2e avoided`, `g PM2.5 prevented`, and `exposure hours protected` using transparent DEFRA/IPCC & EPA AP-42 factors.
6. **BreatheWise AI Copilot**: Thread-based conversational Q&A persisted in PostgreSQL with prompt-injection sanitization, medical-claim guardrails, verified `doc_id` citations, and latency/token observability.
7. **Community Insights**: City-scoped resident observations, clean-air tips, and action pledges with HTML/PII/medical-claim moderation and user reporting—strictly separated from measured sensor readings.

---

## 2. System Architecture

```mermaid
flowchart TB
    subgraph Frontend["Frontend (React 18 + TypeScript + Tailwind + Recharts)"]
        App["Lazy-Loaded App Shell (48 kB main bundle)"]
        Mod["Dashboard | AI Advisor | Indoor | Routine | Impact | Copilot | Community"]
    end

    subgraph Backend["Backend (FastAPI Async + Pydantic v2 + SQLAlchemy 2.0)"]
        Sec["Security Headers + Rate Limiter (120 req/min/IP)"]
        AQI["Separate Indian NAQI & US EPA 2024 Calculators + TTL Cache"]
        Calc["Deterministic IAQ (CADR/ACH) & Sustainability (CO2e/PM2.5) Services"]
        LG["LangGraph 7-Node Advisory Pipeline + Guardrails"]
        RAG["Qdrant Dense + BM25 Hybrid RRF Retriever"]
        Comm["Community Moderation & Reporting Service"]
    end

    subgraph Data["External APIs & Persistence"]
        OM["Open-Meteo AQI & Geocoding"]
        CPCB["CPCB / data.gov.in (Optional API Key)"]
        Gemini["Google Gemini LLM & Embeddings (Optional)"]
        PG[("PostgreSQL 16 / SQLite")]
        Qdrant[("Qdrant Vector DB")]
    end

    Frontend --> Sec
    Sec --> AQI --> OM
    AQI --> CPCB
    Sec --> Calc --> PG
    Sec --> LG --> RAG --> Qdrant
    LG --> Gemini
    Sec --> Comm --> PG
```

---

## 3. Data Provenance & Calculation Audit

### 4-State AQI Provenance
| Provenance | Source | Meaning |
| :--- | :--- | :--- |
| `measured` | CPCB / `data.gov.in` station (when `CPCB_API_KEY` set) | Physical monitoring station pollutant averages |
| `modeled_current` | Open-Meteo Air Quality API (CAMS model) | Current-hour atmospheric model estimate (never labeled `measured`) |
| `forecast` | Open-Meteo Hourly Forecast | Multi-hour modeled trajectory |
| `demo` | Explicit `demo_mode=true` parameter | Synthetic winter-smog reference; never silently substituted for live errors |

### Calculation Methodology & Sources
- **Indian CPCB NAQI (2014)**: Breakpoints for `PM2.5`, `PM10`, `NO2`, `SO2`, `CO` (`mg/m³`), and `O3`, enforcing `>= 3` pollutants including `PM2.5` or `PM10`. Open-Meteo hourly inputs are explicitly tagged `averaging_basis="hourly_modeled_proxy"`.
- **US EPA AQI (May 2024 `PM2.5` Update)**: Official truncation (`PM2.5`/`CO` to 1 decimal, `O3` to 3 decimals, `PM10`/`NO2`/`SO2` to integer), `ROUND_HALF_UP` integer rounding, and 2024 `PM2.5` breakpoints (`0.0–9.0` Good, `9.1–35.4` Moderate, etc.).
- **Indoor Air Quality (ASHRAE 241 / US EPA)**: `CADR (m³/h) = Room Volume (m³) × Target ACH (3.0–6.0)`.
- **Emissions Factors (DEFRA / IPCC & EPA AP-42)**: Petrol car `0.192 kg CO2e/km`, `0.028 g PM2.5/km` vs Metro Rail `0.035 kg CO2e/pkm`, `0.002 g PM2.5/pkm`; open yard-waste burning `~7.6 g PM2.5/kg`. All arithmetic is executed deterministically in Python—never by an LLM.

---

## 4. AI & RAG Architecture
- **Embeddings**: Primary Google Gemini (`models/gemini-embedding-001`), fallback local `sentence-transformers/all-MiniLM-L6-v2` (optional dependency group `local-embeddings`). **Never uses hash vectors**; if neither is available, dense retrieval cleanly disables and falls back to BM25 + curated deterministic guidance.
- **Qdrant Collections**: Dimension-scoped (`{QDRANT_COLLECTION}_d{dim}`), SHA-256 deduplicated, with metadata filtering (`category`, `pollutants`) and relevance thresholds (`RETRIEVAL_SCORE_THRESHOLD=0.25`) so irrelevant chunks are excluded.
- **Security**: Retrieved text is sanitized and wrapped inside `<retrieved_evidence untrusted="true">` delimiters; outputs undergo Pydantic validation, medical-claim blocking, and citation hallucination stripping; observability logs redact `respiratory_conditions`, `name`, and API keys.
- **RAG Evaluation ([backend/app/services/rag_eval.py](backend/app/services/rag_eval.py))**: 6-case benchmark measuring contextual precision, contextual recall, citation correctness, answer relevancy, and faithfulness without requiring an LLM judge.

---

## 5. Setup, Migration & Deployment

### 1. Environment Variables
```bash
cp .env.example .env
```
Never commit `.env` or API keys. Leave `GEMINI_API_KEY` and `CPCB_API_KEY` blank for deterministic/Open-Meteo mode, or populate them for live Gemini & CPCB station support.

### 2. Local Development
**Backend**:
```powershell
cd backend
.\.venv\Scripts\python.exe -m app.db.migrate
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Swagger UI: `http://127.0.0.1:8000/docs`

**Frontend**:
```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```
App URL: `http://127.0.0.1:5173`

### 3. Docker Compose Production Deployment (PostgreSQL 16 + Qdrant + FastAPI + Nginx)
```bash
docker compose config
docker compose up --build -d
```
- Frontend (Nginx + `/api` reverse proxy): `http://localhost:3000`
- Backend API & Swagger: `http://localhost:8000/docs`
- Health Check: `GET http://localhost:8000/api/v1/health` (verifies DB connectivity & Qdrant mode)
- Persistent volumes: `postgres_data`, `qdrant_data`

### 4. Troubleshooting
- **PowerShell script policy blocks `npm`**: Use `npm.cmd` on Windows.
- **`data.gov.in` CPCB timeout**: `data.gov.in` requires a registered `CPCB_API_KEY` and can experience upstream timeouts; BreatheWise automatically falls back to Open-Meteo `modeled_current` without fabricating `measured` readings.
- **No `GEMINI_API_KEY`**: LangGraph executes `deterministic_fallback` transparently with full citations and calculations.

---

## 6. Verification & Testing Commands
```powershell
# Backend (Pytest: unit, integration, RAG eval, security, persistence)
cd backend
.\.venv\Scripts\python.exe -m pytest -v

# Optional Dockerized PostgreSQL + Qdrant live container test
$env:TEST_POSTGRES_URL="postgresql+asyncpg://breathewise:breathewise@localhost:5432/breathewise"
$env:TEST_QDRANT_URL="http://localhost:6333"
.\.venv\Scripts\python.exe -m pytest tests/test_persistence_and_docker_ready.py -v

# Frontend (TypeScript, Vite production build, Vitest)
cd ..\frontend
npm.cmd run build
npm.cmd test
```

---

## 7. API Reference
- `GET /api/v1/health` — Service, DB, Qdrant, Gemini, and CPCB readiness
- `GET /api/v1/aqi/current`, `GET /api/v1/aqi/forecast`, `GET /api/v1/aqi/locations/search`
- `POST /api/v1/profiles`, `GET /api/v1/profiles/{profile_id}`
- `POST /api/v1/advisor/recommendations`, `POST /api/v1/advisor/indoor`, `POST /api/v1/advisor/routine`
- `GET /api/v1/impact/catalog`, `POST /api/v1/impact/actions`, `GET /api/v1/impact/summary`, `DELETE /api/v1/impact/actions/{id}`
- `POST /api/v1/chat`
- `GET /api/v1/community/posts`, `POST /api/v1/community/posts`, `POST /api/v1/community/posts/{id}/upvote`, `POST /api/v1/community/posts/{id}/report`, `GET /api/v1/community/summary`

---

## 8. Assumptions Made & Known Limitations

### Assumptions Made
1. **Hourly AQI Proxy for Modeled Data**: Official Indian NAQI (`24h` mean for PM/NO2/SO2, `8h` mean for CO/O3) and US EPA AQI breakpoints are applied to Open-Meteo current-hour modeled concentrations as an actionable proxy and explicitly tagged `averaging_basis="hourly_modeled_proxy"`.
2. **CPCB Live Station Mapping**: When `CPCB_API_KEY` is configured for Indian cities, `aqi_service.py` selects the first active monitoring station reporting `PM2.5` and `>= 3` pollutants, and converts small numeric `CO` values (`< 20`) from `mg/m³` to canonical `µg/m³`.
3. **Indoor CADR Sizing Model**: Assumes well-mixed single-room air volume (`area × ceiling height × 0.0283168`) and standard clean-room targets (`3.0–6.0 ACH` depending on outdoor severity and occupant vulnerability), plus typical home envelope infiltration assumptions.
4. **Sustainability Emission Factors**: Uses fixed fleet-average emission factors (e.g., DEFRA/IPCC petrol car `0.192 kg CO2e/km`, metro `0.035 kg CO2e/pkm`; `4.33 weeks/month`) rather than live vehicle telematics; outputs are labeled as estimates, never measured reductions.
5. **Forecast Uncertainty**: 24-hour lowest-exposure windows compare relative modeled dispersion dips and never guarantee safe outdoor air.

### Known Limitations
1. Official CPCB station measurements require a user-supplied `data.gov.in` `CPCB_API_KEY`; otherwise live readings come from Open-Meteo CAMS atmospheric models (`modeled_current` / `forecast`).
2. `sentence-transformers` is an optional dependency (`local-embeddings` in `pyproject.toml`); without it and without `GEMINI_API_KEY`, RAG operates in BM25 + curated deterministic mode.
3. Heavy charting (`recharts`) is code-split into a lazy vendor chunk (`~531 kB` raw / `~152 kB` gzip) loaded only when chart views mount.

---

## 9. Hackathon Submission Kit

### Suggested 3-Minute Live Demo Flow
1. **0:00–0:40 — Dashboard & Provenance**: Show Delhi live `Modeled Current` (`Indian NAQI` vs `US EPA 2024` side-by-side) and 24h forecast chart; toggle `Demo Mode` to illustrate transparent severe winter-smog testing.
2. **0:40–1:15 — Household Profile & AI Recommendations**: Load `default-family` profile; show LangGraph trace, `Exposure Reduction` vs `Emissions Reduction` badges, deterministic metro `kg CO2e` / `g PM2.5` swap, and WHO/CPCB/EPA citations.
3. **1:15–1:50 — Indoor Air Advisor & Routine Planner**: Enter room dimensions (`250 sq ft`) to compute `CADR`/`ACH` and ventilation window; show Routine Planner's forecast-uncertainty notice and hourly schedule.
4. **1:50–2:30 — Sustainability Tracker & AI Copilot**: Log a metro commute action and watch the 7-day chart update from persisted DB logs; ask Copilot a question and inspect cited evidence cards.
5. **2:30–3:00 — Community Insights & Moderation**: Post a neighborhood pledge, show user-contributed provenance separation, and demonstrate PII/medical-claim moderation protection.

### Technical Blog Outline: *"Designing Honest GenAI for Urban Air Quality"*
1. **Why Raw AQI Numbers Fail Families** (and why mixing CPCB NAQI with US EPA AQI misleads users).
2. **Four-State Data Provenance** (`measured`, `modeled_current`, `forecast`, `demo`) as a first-class API contract.
3. **Deterministic Science + Bounded LLMs**: Keeping CADR, AQI breakpoints, and CO2e math in Python while LangGraph handles synthesis, citations, and safety fallbacks.
4. **Honest RAG**: Rejecting hash embeddings, handling missing embedding providers via BM25, and sanitizing untrusted retrieved chunks.
5. **From Exposure Reduction to Community Action**: Closing the loop with persisted sustainability tracking and moderated neighborhood insights.
