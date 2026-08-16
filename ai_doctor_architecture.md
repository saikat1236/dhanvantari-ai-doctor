# Chat/Voice AI Doctor — System Architecture (Python)

**Status note (Aug 2026):** Med-PaLM was a Google Research paper model, never a public API. Its Vertex AI product, MedLM, was deprecated Sept 29, 2025 and is no longer provisionable. This architecture targets **MedGemma 1.5** (open-weight, released Jan 2026, self-hostable) as the primary clinical LLM, with **MedASR** (Google's open medical speech model, same release) for the voice pipeline, and Gemini/Vertex as a general-purpose fallback for conversational fluency. Swap the model provider without touching anything else — that's the point of the abstraction layer in §6.2.

---

## 1. Design constraints that shape everything

Before the stack: two constraints aren't optional, they're regulatory.

- **India's Telemedicine Practice Guidelines (2020)** require a Registered Medical Practitioner (RMP) in the loop for diagnosis and prescription. A fully autonomous AI cannot legally issue a prescription. This pushes the architecture toward **triage + draft + human sign-off**, not autonomous diagnosis.
- **DPDP Act 2023** governs how you store and process patient health data (a "sensitive personal data" category under most readings). You need consent capture, purpose limitation, and a data-retention policy baked in from day one, not bolted on later.

If you're building this for a US audience instead, swap DPDP considerations for HIPAA (BAA with your cloud provider, encryption at rest/in transit, audit logging of every PHI access) — the architecture below doesn't change, only the compliance layer's specifics do.

Practically: treat the system as a **symptom-checker + triage + doctor-connect** product, not a replacement for a doctor. That framing is what the "Safety & human oversight" layer in the diagram enforces structurally, not just in prompt wording.

---

## 2. High-level layers (recap of the diagram above)

1. **Client** — chat UI + voice UI (mic in, speaker out)
2. **Orchestration** — API gateway (FastAPI) + conversation orchestrator (stateful agent)
3. **Intelligence** — LLM layer (MedGemma primary, Gemini fallback) + RAG knowledge grounding
4. **Safety & human oversight** — red-flag/emergency guardrails + doctor review queue
5. **Data & compliance** — patient records, audit/consent log

Everything below expands each layer into actual modules and code.

---

## 3. Repository structure

```
ai-doctor/
├── app/
│   ├── main.py                      # FastAPI app entrypoint
│   ├── config.py                    # env-driven settings (pydantic-settings)
│   ├── routers/
│   │   ├── chat.py                  # POST /chat, WS /chat/stream
│   │   ├── voice.py                 # POST /voice (audio in/out), WS /voice/stream
│   │   ├── auth.py                  # login, token refresh, consent capture
│   │   └── admin.py                 # doctor review queue endpoints
│   ├── orchestrator/
│   │   ├── graph.py                 # LangGraph state machine definition
│   │   ├── state.py                 # ConversationState schema
│   │   └── nodes/
│   │       ├── intake.py
│   │       ├── symptom_collector.py
│   │       ├── safety_check.py      # red-flag / emergency detection
│   │       ├── retrieve.py          # RAG lookup
│   │       ├── generate.py          # LLM call + response drafting
│   │       └── triage_router.py     # decide: self-care / OTC info / escalate to RMP
│   ├── llm/
│   │   ├── base.py                  # LLMProvider abstract interface
│   │   ├── medgemma_provider.py     # self-hosted vLLM MedGemma client
│   │   ├── vertex_provider.py       # Vertex AI Gemini fallback
│   │   └── router.py                # picks provider, handles failover
│   ├── voice/
│   │   ├── stt.py                   # MedASR / Whisper wrapper
│   │   ├── tts.py                   # Google Cloud TTS / Coqui wrapper
│   │   └── vad.py                   # voice activity detection for streaming
│   ├── rag/
│   │   ├── ingest.py                # embeds and loads medical corpus
│   │   ├── retriever.py             # vector search + reranking
│   │   └── sources/                 # MedlinePlus, ICD-10, clinical guideline docs
│   ├── safety/
│   │   ├── red_flags.py             # emergency symptom classifier + rules
│   │   ├── guardrail_prompts.py     # system prompts enforcing disclaimers/scope
│   │   └── escalation.py            # routes to human RMP queue
│   ├── models/                      # SQLAlchemy models: Patient, Conversation, Message, ReviewItem
│   ├── db/
│   │   ├── session.py
│   │   └── migrations/              # alembic
│   ├── auth/
│   │   ├── jwt.py
│   │   └── consent.py               # DPDP-style consent record
│   └── observability/
│       ├── logging.py
│       └── tracing.py               # LangSmith / OpenTelemetry
├── tests/
├── deploy/
│   ├── docker-compose.yml           # local dev: api, postgres, redis, vllm
│   ├── vllm/Dockerfile              # MedGemma inference server
│   └── k8s/                         # production manifests
├── pyproject.toml
└── .env.example
```

---

## 4. Tech stack

| Concern | Choice | Why |
|---|---|---|
| API framework | FastAPI + Uvicorn/Gunicorn | async, WebSocket support for streaming voice/chat |
| Orchestration | LangGraph | explicit state machine — needed for triage logic, not a black-box agent loop |
| Primary LLM | MedGemma 1.5 (27B text or 4B multimodal) via vLLM | open weight, self-hostable, clinically tuned |
| Fallback LLM | Gemini via Vertex AI | conversational fluency, multilingual (useful for Hindi/Bengali patients) |
| Speech-to-text | MedASR (clinical terms) + faster-whisper (general fallback) | MedASR for accuracy on medical vocabulary, Whisper for robustness to accents/casual speech |
| Text-to-speech | Google Cloud TTS (or Coqui for self-hosted) | natural voices, streaming support |
| Vector DB | pgvector (Postgres extension) or Weaviate | keeps infra simple if already on Postgres |
| Relational DB | PostgreSQL | patient records, conversation history, audit logs |
| Cache/session | Redis | conversation state between turns, rate limiting |
| Auth | JWT (short-lived) + refresh tokens | standard; add OTP for patient-facing login in India |
| Task queue | Celery or Arq | async doctor-notification, report generation |
| Observability | LangSmith or Langfuse + Prometheus/Grafana | trace every LLM call — critical for a medical product's audit trail |
| Deployment | GCP (Cloud Run for API, GKE or Compute Engine + vLLM for MedGemma, Vertex AI for Gemini fallback) | matches where MedGemma/MedASR are natively supported |

---

## 5. Conversation state schema

```python
# app/orchestrator/state.py
from typing import TypedDict, Literal
from pydantic import BaseModel

class SymptomEntry(BaseModel):
    description: str
    onset: str | None = None
    severity: int | None = None  # 1-10

class ConversationState(TypedDict):
    session_id: str
    patient_id: str
    turns: list[dict]              # raw message history
    symptoms: list[SymptomEntry]
    red_flag_detected: bool
    red_flag_reason: str | None
    retrieved_context: list[str]   # RAG chunks used to ground the response
    triage_level: Literal["self_care", "see_doctor_soon", "urgent", "emergency"] | None
    escalated_to_rmp: bool
    draft_response: str | None
```

---

## 6. Core modules

### 6.1 Orchestrator graph (LangGraph)

```python
# app/orchestrator/graph.py
from langgraph.graph import StateGraph, END
from app.orchestrator.state import ConversationState
from app.orchestrator.nodes import (
    intake, symptom_collector, safety_check, retrieve, generate, triage_router,
)

def build_graph():
    g = StateGraph(ConversationState)

    g.add_node("intake", intake.run)
    g.add_node("collect_symptoms", symptom_collector.run)
    g.add_node("safety_check", safety_check.run)
    g.add_node("retrieve", retrieve.run)
    g.add_node("generate", generate.run)
    g.add_node("triage", triage_router.run)

    g.set_entry_point("intake")
    g.add_edge("intake", "collect_symptoms")
    g.add_edge("collect_symptoms", "safety_check")

    # Safety check is the hard gate: emergency short-circuits straight to the
    # user-facing emergency response, bypassing generation entirely.
    g.add_conditional_edges(
        "safety_check",
        lambda s: "emergency" if s["red_flag_detected"] else "continue",
        {"emergency": END, "continue": "retrieve"},
    )

    g.add_edge("retrieve", "generate")
    g.add_edge("generate", "triage")
    g.add_edge("triage", END)

    return g.compile()
```

### 6.2 LLM provider abstraction

```python
# app/llm/base.py
from abc import ABC, abstractmethod

class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, system_prompt: str, messages: list[dict], **kwargs) -> str:
        ...

# app/llm/medgemma_provider.py
import httpx
from app.llm.base import LLMProvider

class MedGemmaProvider(LLMProvider):
    """Talks to a self-hosted vLLM server running MedGemma 1.5."""
    def __init__(self, base_url: str):
        self.client = httpx.AsyncClient(base_url=base_url, timeout=30)

    async def generate(self, system_prompt: str, messages: list[dict], **kwargs) -> str:
        payload = {
            "model": "medgemma-1.5-27b",
            "messages": [{"role": "system", "content": system_prompt}, *messages],
            "temperature": kwargs.get("temperature", 0.3),
        }
        resp = await self.client.post("/v1/chat/completions", json=payload)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

# app/llm/router.py
class LLMRouter:
    """Primary/fallback with automatic failover — never let a single
    provider outage take the whole system down."""
    def __init__(self, primary: LLMProvider, fallback: LLMProvider):
        self.primary, self.fallback = primary, fallback

    async def generate(self, *args, **kwargs) -> str:
        try:
            return await self.primary.generate(*args, **kwargs)
        except Exception:
            return await self.fallback.generate(*args, **kwargs)
```

### 6.3 Safety guardrails — the layer that actually matters most

```python
# app/safety/red_flags.py
RED_FLAG_PATTERNS = {
    "chest_pain": ["chest pain", "crushing pain", "pain radiating to arm"],
    "breathing": ["can't breathe", "shortness of breath", "gasping"],
    "stroke": ["face drooping", "slurred speech", "sudden weakness one side"],
    "bleeding": ["heavy bleeding", "won't stop bleeding"],
    "suicidal": ["want to die", "end my life", "suicide"],
    "pediatric_high_fever": ["baby fever", "infant fever", "newborn temperature"],
}

def detect_red_flag(text: str) -> tuple[bool, str | None]:
    lowered = text.lower()
    for category, patterns in RED_FLAG_PATTERNS.items():
        if any(p in lowered for p in patterns):
            return True, category
    return False, None

# app/orchestrator/nodes/safety_check.py
from app.safety.red_flags import detect_red_flag

EMERGENCY_RESPONSE = (
    "This sounds like it could be a medical emergency. Please call 108 "
    "(ambulance) or 112 immediately, or go to the nearest emergency room. "
    "I'm not able to help further with this — please get in-person care now."
)

async def run(state):
    last_user_msg = state["turns"][-1]["content"]
    is_red_flag, reason = detect_red_flag(last_user_msg)
    state["red_flag_detected"] = is_red_flag
    state["red_flag_reason"] = reason
    if is_red_flag:
        state["draft_response"] = EMERGENCY_RESPONSE
    return state
```

Two things worth calling out about this layer specifically:

- **Rules before models.** The red-flag check runs as deterministic pattern matching *before* any LLM call, not as an LLM judgment. An emergency detector that itself depends on model inference is a single point of failure you don't want in a medical product. Use the LLM to *supplement* this (catch phrasing the rules miss) but never *replace* the rules.
- **The graph structure enforces the gate.** Because `safety_check` short-circuits to `END` on the conditional edge, there's no code path where a red-flag message reaches the generation node. That's a structural guarantee, not a prompt instruction — prompt instructions can be argued around by adversarial input, graph topology can't.

### 6.4 Voice pipeline

```python
# app/voice/stt.py
class SpeechToText:
    """Routes to MedASR for clinical accuracy, falls back to Whisper for
    speech it's less confident about (patients don't talk like doctors dictate)."""
    def __init__(self, medasr_client, whisper_model):
        self.medasr = medasr_client
        self.whisper = whisper_model

    async def transcribe(self, audio_bytes: bytes) -> str:
        result = await self.medasr.transcribe(audio_bytes)
        if result.confidence < 0.6:
            result = self.whisper.transcribe(audio_bytes)
        return result.text

# app/voice/tts.py
class TextToSpeech:
    def __init__(self, client):
        self.client = client

    async def synthesize(self, text: str, voice="en-IN-Standard-A") -> bytes:
        return await self.client.synthesize_speech(text=text, voice=voice)
```

---

## 7. Sequence flow — one voice consultation, end to end

1. Patient taps mic in the app → audio streams over WebSocket to `/voice/stream`.
2. `stt.py` transcribes in near-real-time (MedASR primary, Whisper fallback).
3. Transcript enters the LangGraph orchestrator at `intake`.
4. `collect_symptoms` extracts structured symptom data from free text (onset, severity, duration).
5. `safety_check` runs red-flag detection. If triggered → emergency response returned immediately, TTS speaks it, conversation logged and flagged for review. **Flow stops here for red flags.**
6. If clear, `retrieve` pulls grounding context from the RAG knowledge base (clinical guidelines, MedlinePlus-derived content) relevant to the symptoms.
7. `generate` calls the LLM router (MedGemma primary) with the system prompt, conversation history, and retrieved context to draft a response — informational, not diagnostic in tone.
8. `triage_router` classifies the response into `self_care` / `see_doctor_soon` / `urgent`, and for anything beyond self-care, queues an entry in the doctor review queue.
9. Response is spoken back via TTS and also shown as text (accessibility + record-keeping).
10. Every turn — transcript, retrieved context, model output, triage decision — is written to the audit log with timestamps, satisfying the DPDP/compliance trail.

---

## 8. Data layer essentials

```python
# app/models/core.py (SQLAlchemy, abbreviated)
class Patient(Base):
    id: Mapped[str] = mapped_column(primary_key=True)
    consent_given_at: Mapped[datetime | None]
    consent_scope: Mapped[str]           # what they consented to, DPDP-style

class Conversation(Base):
    id: Mapped[str] = mapped_column(primary_key=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patient.id"))
    started_at: Mapped[datetime]
    triage_level: Mapped[str | None]

class Message(Base):
    id: Mapped[str] = mapped_column(primary_key=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversation.id"))
    role: Mapped[str]                    # user / assistant / system
    content: Mapped[str]
    red_flag_detected: Mapped[bool]

class ReviewItem(Base):
    """Doctor review queue — anything beyond self-care lands here for RMP sign-off."""
    id: Mapped[str] = mapped_column(primary_key=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversation.id"))
    status: Mapped[str]                  # pending / reviewed / prescribed
    reviewing_rmp_id: Mapped[str | None]
```

---

## 9. Deployment

- **API layer (FastAPI):** Cloud Run — scales to zero, cheap for early-stage traffic.
- **MedGemma inference:** vLLM server on a GPU-backed Compute Engine instance or GKE node pool (MedGemma 27B needs a decent GPU — an L4 or A100 depending on latency targets; the 4B multimodal variant is far cheaper if you don't need top-end reasoning).
- **Gemini fallback:** Vertex AI, no infra to manage.
- **Postgres + pgvector:** Cloud SQL.
- **Redis:** Memorystore.
- **Secrets:** Secret Manager, never in `.env` committed to git.

For an MVP/pilot, it's entirely reasonable to run MedGemma 4B on a single GPU VM and skip GKE until traffic justifies it — don't over-engineer the infra before the product is validated.

---

## 10. Phased build order

1. **Phase 1 — text-only triage bot.** Chat UI, FastAPI, MedGemma via vLLM, safety guardrails, RAG. No voice yet. This alone validates the hardest part (safety + triage logic).
2. **Phase 2 — add voice.** STT/TTS pipeline, streaming WebSocket support.
3. **Phase 3 — doctor review loop.** Review queue UI, RMP sign-off flow, prescription drafting (RMP-signed, not AI-signed).
4. **Phase 4 — EHR integration, multilingual support (Hindi/Bengali via Gemini), analytics.**

Build and validate Phase 1 completely — including a red-team pass specifically trying to get the safety guardrails to miss an emergency — before adding voice. Voice adds latency and transcription-error surface area on top of a system whose correctness you haven't proven yet.
