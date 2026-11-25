import hashlib
import io
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from pypdf import PdfReader


@dataclass(frozen=True)
class KnowledgeDocument:
    doc_id: str
    title: str
    source_org: str
    source_url: str
    doc_version: str
    category: str  # health | indoor | grap_policy | commute | iaq_engineering
    pollutants: List[str]
    content: str


@dataclass(frozen=True)
class KnowledgeChunk:
    chunk_id: str
    doc_id: str
    title: str
    source_org: str
    source_url: str
    doc_version: str
    category: str
    pollutants: List[str]
    chunk_index: int
    text: str
    content_hash: str
    ingested_at: str


def compute_content_hash(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def chunk_text(text: str, chunk_size: int = 650, overlap: int = 80) -> List[str]:
    """Deterministically split text into overlapping character chunks aligned on word boundaries."""
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    if len(cleaned) <= chunk_size:
        return [cleaned]

    chunks: List[str] = []
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + chunk_size)
        if end < len(cleaned):
            space_idx = cleaned.rfind(" ", start + int(chunk_size * 0.5), end)
            if space_idx > start:
                end = space_idx
        piece = cleaned[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(cleaned):
            break
        start = max(end - overlap, start + 1)
    return chunks


def build_chunks_from_document(doc: KnowledgeDocument, chunk_size: int = 650, overlap: int = 80) -> List[KnowledgeChunk]:
    """Chunk a KnowledgeDocument while preserving version, source attribution, and content hashes."""
    now_iso = datetime.now(timezone.utc).isoformat()
    pieces = chunk_text(doc.content, chunk_size=chunk_size, overlap=overlap)
    result: List[KnowledgeChunk] = []
    for idx, piece in enumerate(pieces):
        chunk_id = f"{doc.doc_id}::v{doc.doc_version}::c{idx}"
        result.append(
            KnowledgeChunk(
                chunk_id=chunk_id,
                doc_id=doc.doc_id,
                title=doc.title,
                source_org=doc.source_org,
                source_url=doc.source_url,
                doc_version=doc.doc_version,
                category=doc.category,
                pollutants=list(doc.pollutants),
                chunk_index=idx,
                text=piece,
                content_hash=compute_content_hash(piece),
                ingested_at=now_iso,
            )
        )
    return result


def ingest_text_document(
    *,
    doc_id: str,
    title: str,
    text: str,
    source_org: str,
    category: str,
    pollutants: Optional[List[str]] = None,
    source_url: str = "",
    doc_version: str = "1.0",
) -> List[KnowledgeChunk]:
    """Ingest a raw text document into versioned, attributed KnowledgeChunks."""
    doc = KnowledgeDocument(
        doc_id=doc_id,
        title=title,
        source_org=source_org,
        source_url=source_url,
        doc_version=doc_version,
        category=category,
        pollutants=pollutants or ["PM2.5", "PM10"],
        content=text,
    )
    return build_chunks_from_document(doc)


def ingest_pdf_bytes(
    *,
    pdf_bytes: bytes,
    doc_id: str,
    title: Optional[str] = None,
    source_org: str = "Uploaded PDF",
    category: str = "health",
    pollutants: Optional[List[str]] = None,
    source_url: str = "",
    doc_version: str = "1.0",
) -> List[KnowledgeChunk]:
    """Extract text and PDF metadata from PDF bytes and return attributed KnowledgeChunks."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    meta_title = None
    if reader.metadata and getattr(reader.metadata, "title", None):
        meta_title = str(reader.metadata.title).strip()

    extracted_pages: List[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text.strip():
            extracted_pages.append(page_text.strip())

    combined = "\n".join(extracted_pages)
    if not combined.strip():
        return []

    doc = KnowledgeDocument(
        doc_id=doc_id,
        title=title or meta_title or doc_id,
        source_org=source_org,
        source_url=source_url,
        doc_version=doc_version,
        category=category,
        pollutants=pollutants or ["PM2.5", "PM10"],
        content=combined,
    )
    return build_chunks_from_document(doc)


CURATED_KNOWLEDGE_DOCUMENTS: List[KnowledgeDocument] = [
    KnowledgeDocument(
        doc_id="who_aqg_2021",
        title="WHO Global Air Quality Guidelines (2021) — Health Thresholds & Sensitive Groups",
        source_org="World Health Organization (WHO)",
        source_url="https://www.who.int/publications/i/item/9789240034228",
        doc_version="2021.1",
        category="health",
        pollutants=["PM2.5", "PM10", "NO2", "O3", "SO2", "CO"],
        content=(
            "WHO Global Air Quality Guidelines (2021) set a 24-hour guideline level of 15 µg/m³ for PM2.5 "
            "(annual 5 µg/m³), 45 µg/m³ for PM10 (annual 15 µg/m³), 25 µg/m³ for NO2 (24-hour), 40 µg/m³ for SO2 "
            "(24-hour), and 100 µg/m³ for O3 (8-hour daily maximum). Fine particulate matter (PM2.5) penetrates deep "
            "into the alveoli and bloodstream, elevating respiratory and cardiovascular irritation risks, especially "
            "for children, older adults, pregnant individuals, and people with asthma or COPD. Reducing outdoor "
            "vigorous exertion during high-PM2.5 hours lowers inhaled particle dose, though no protective measure "
            "guarantees complete immunity from air pollution effects."
        ),
    ),
    KnowledgeDocument(
        doc_id="cpcb_grap_stages",
        title="CPCB NAQI & CAQM Graded Response Action Plan (GRAP) Stages I–IV",
        source_org="Central Pollution Control Board (CPCB) & CAQM India",
        source_url="https://cpcb.nic.in/",
        doc_version="2024.1",
        category="grap_policy",
        pollutants=["PM2.5", "PM10", "NO2", "CO"],
        content=(
            "Under India's CPCB National Air Quality Index (NAQI) and CAQM Graded Response Action Plan (GRAP): "
            "Stage I (Poor, NAQI 201–300) enforces dust control, anti-smog water sprinkling, ban on open waste "
            "burning, and public transit encouragement. Stage II (Very Poor, NAQI 301–400) restricts diesel generators, "
            "increases metro/bus frequency, and advises sensitive groups to avoid prolonged outdoor exertion. "
            "Stage III (Severe, NAQI 401–450) halts non-essential construction, restricts BS-III petrol and BS-IV "
            "diesel four-wheelers in NCR, and supports hybrid/online classes for younger students. Stage IV (Severe+, "
            "NAQI >450) restricts heavy diesel trucks, encourages 50% work-from-home, and strongly advises staying indoors "
            "with clean air filtration."
        ),
    ),
    KnowledgeDocument(
        doc_id="epa_indoor_clean_room",
        title="US EPA Clean Room, Indoor Source Control & N95 Respirator Guidance",
        source_org="United States Environmental Protection Agency (US EPA)",
        source_url="https://www.epa.gov/indoor-air-quality-iaq",
        doc_version="2024.1",
        category="indoor",
        pollutants=["PM2.5", "PM10", "NO2", "CO", "O3"],
        content=(
            "US EPA recommends creating a designated clean room during severe particulate smoke or winter smog: "
            "keep exterior doors and windows closed, weatherstrip leaky gaps, run a properly sized true HEPA purifier "
            "(avoiding ozone-generating air cleaners or ionizers that emit ozone), and avoid indoor combustion sources "
            "such as incense, candles, tobacco smoke, or unvented gas cooking. Use externally vented range hoods while "
            "cooking and wet-mop floors instead of dry sweeping so coarse PM10 does not resuspend. When outdoor "
            "travel is unavoidable during Unhealthy/Poor or worse conditions, a well-fitted N95 or FFP2 respirator "
            "(without exhalation gap leaks) filters fine PM2.5 particles far more effectively than cloth or loose surgical masks."
        ),
    ),
    KnowledgeDocument(
        doc_id="ashrae_241_filtration",
        title="ASHRAE / CDC Indoor Filtration Sizing, CADR, ACH & Corsi-Rosenthal DIY Box",
        source_org="ASHRAE / CDC Indoor Air Quality Guidance",
        source_url="https://www.ashrae.org/",
        doc_version="2023.1",
        category="iaq_engineering",
        pollutants=["PM2.5", "PM10"],
        content=(
            "Air purifier sizing is governed by Clean Air Delivery Rate (CADR) and room volume: Required CADR (m³/h) = "
            "Room Volume (m³) × Target Air Changes per Hour (ACH). During moderate air quality, 3–4 ACH is typical, "
            "rising to 4.5–6 ACH during severe winter smog or sensitive-occupant protection. Where commercial HEPA "
            "units are cost-prohibitive, a DIY Corsi-Rosenthal box built by taping four MERV-13 pleated furnace filters "
            "to a box fan provides high-CADR particulate filtration at low cost. Indoor filtration reduces personal "
            "indoor exposure only and never alters outdoor ambient AQI."
        ),
    ),
    KnowledgeDocument(
        doc_id="winter_inversion_routine",
        title="Winter Boundary-Layer Inversion Physics & Smart Routine Timing",
        source_org="Urban Atmospheric Science & Public Health Synthesis",
        source_url="https://www.epa.gov/air-research",
        doc_version="1.0",
        category="commute",
        pollutants=["PM2.5", "PM10", "NO2", "CO"],
        content=(
            "During cold winter mornings and late evenings, radiation temperature inversions trap vehicle exhaust, "
            "biomass smoke, and road dust inside a shallow atmospheric boundary layer near ground level, causing steep "
            "PM2.5, NO2, and CO spikes between roughly 06:00–10:00 and 19:00–23:00 local time. Solar surface heating "
            "typically deepens the mixing layer in early-to-mid afternoon (around 12:30–16:00), lowering ground-level "
            "particulate concentrations unless synoptic fog persists. Scheduling errands, brief window airing, or "
            "low-intensity outdoor movement during the afternoon trough reduces inhaled exposure compared to peak rush hours."
        ),
    ),
    KnowledgeDocument(
        doc_id="low_emission_commute_swaps",
        title="Low-Emission Urban Mobility & Exposure vs. Emissions Distinction",
        source_org="DEFRA / IPCC & Urban Clean Mobility Guidelines",
        source_url="https://www.gov.uk/government/collections/government-conversion-factors-for-company-reporting",
        doc_version="2024.1",
        category="commute",
        pollutants=["PM2.5", "NO2", "CO"],
        content=(
            "Shifting a daily petrol passenger-car commute (~0.192 kg CO2e/km) to electric metro rail (~0.035 kg "
            "CO2e/passenger-km) or working from home eliminates direct tailpipe CO2e, NO2, and street-level brake/exhaust "
            "PM2.5 emissions. Importantly, emissions reduction (avoiding kg CO2e and g PM2.5 emitted into the city airshed) "
            "is distinct from personal exposure reduction: walking or cycling along congested arterial roads during severe "
            "smog has zero tailpipe emissions but high personal inhalation dose due to elevated breathing rate near traffic. "
            "During severe AQI, enclosed metro transit or WFH lowers both emissions and personal exposure."
        ),
    ),
]


def get_curated_chunks(chunk_size: int = 650, overlap: int = 80) -> List[KnowledgeChunk]:
    """Return all curated authoritative chunks ready for indexing or deterministic lookup."""
    all_chunks: List[KnowledgeChunk] = []
    for doc in CURATED_KNOWLEDGE_DOCUMENTS:
        all_chunks.extend(build_chunks_from_document(doc, chunk_size=chunk_size, overlap=overlap))
    return all_chunks
