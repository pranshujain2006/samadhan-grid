"""SAMADHAN GRID - Jharkhand Problem-to-Impact Innovation Operating System.

FastAPI application entry point.
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import seed as seed_mod
from .ai import groq_client
from .config import STATIC_DIR, UPLOAD_DIR
from .db import close, connect, db, ledger, new_id
from .routers import analytics, challenges, governance, projects, satisfaction, story

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s - %(message)s")
log = logging.getLogger("samadhan")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect()
    counts = await seed_mod.seed_reference_data()
    log.info("Connected to MongoDB. Reference data: %s", counts)
    await groq_client.resolve_model()   # confirm the account has a usable chat model
    log.info("AI mode: %s (chat=%s, stt=%s)", groq_client.status()["mode"],
             groq_client.active_model(), groq_client.status()["stt_model"])
    if os.getenv("EPHEMERAL_DISK", "").lower() in ("1", "true", "yes"):
        log.warning("EPHEMERAL_DISK is set: uploaded evidence files are wiped on every "
                    "restart. Fine for a demo; use object storage for real deployments.")
    yield
    await close()


app = FastAPI(
    title="SAMADHAN GRID",
    description=("Jharkhand Problem-to-Impact Innovation Operating System. "
                 "Citizen voice -> Problem DNA -> validated challenge -> university & "
                 "industry coalition -> field-tested solution -> measured community impact."),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])

app.include_router(challenges.router)
app.include_router(governance.router)
app.include_router(projects.router)
app.include_router(analytics.router)
app.include_router(story.router)
app.include_router(satisfaction.router)

meta = APIRouter(prefix="/api", tags=["meta"])


@meta.get("/health")
async def health() -> dict[str, Any]:
    try:
        await db().command("ping")
        mongo = "connected"
    except Exception as exc:  # noqa: BLE001
        mongo = f"error: {exc}"
    return {"status": "ok", "mongodb": mongo, "ai": groq_client.status()}


@meta.post("/seed/reference")
async def seed_reference(force: bool = False) -> dict[str, Any]:
    return await seed_mod.seed_reference_data(force=force)


@meta.post("/demo/bootstrap")
async def bootstrap_demo(reset: bool = False) -> dict[str, Any]:
    """Load the demo scenario: 8 citizen reports, mostly the Khunti water cluster.

    Each report runs through the real pipeline (Problem DNA -> priority -> dedup),
    so what you see afterwards is genuine engine output, not canned data.
    """
    d = db()
    if reset:
        for coll in ("challenges", "projects", "constellations", "missions",
                     "coalitions", "feedback", "ledger", "evidence"):
            await d[coll].delete_many({})

    if await d.challenges.count_documents({}) > 0 and not reset:
        return {"skipped": True,
                "message": "Demo data already present. Call with ?reset=true to reload.",
                "challenges": await d.challenges.count_documents({})}

    await seed_mod.seed_reference_data()
    created: list[dict[str, Any]] = []

    for rep in seed_mod.DEMO_REPORTS:
        location = {
            "state": "Jharkhand", "district": rep["district"], "block": rep["block"],
            "panchayat_or_ulb": rep["panchayat_or_ulb"],
            "village_or_ward": rep["village_or_ward"],
            "lat": rep["lat"], "lon": rep["lon"], "coords_source": "gps",
        }
        result = await challenges._run_pipeline(
            rep["text"], rep["language"], location, [], rep["channel"],
            rep["channel"] == "csc_assisted")

        created_at = seed_mod._dt(rep["days_ago"])
        cid = new_id("CH")
        doc = {
            "challenge_id": cid, "status": "ai_processed", "route": None,
            "raw": {"text": rep["text"], "language": rep["language"],
                    "channel": rep["channel"], "reporter_name": rep["reporter"],
                    "reporter_contact": None, "assisted_by": None},
            "dna": result["dna"], "location": location, "evidence": [],
            "priority": result["priority"],
            "official_priority": None,
            "evidence_confidence": result["evidence_confidence"],
            "officer_brief": result["officer_brief"], "related": result["related"],
            "independent_reports": result["independent_reports"],
            "master_challenge_id": None, "corroborates": [], "constellation_id": None,
            "project_id": None, "review": None,
            "created_at": created_at, "updated_at": created_at,
        }
        await d.challenges.insert_one(dict(doc))
        await ledger(cid, "challenge", "citizen_report_submitted", rep["reporter"],
                     "citizen", {"channel": rep["channel"], "district": rep["district"],
                                 "language": rep["language"]})
        await ledger(cid, "challenge", "ai_problem_dna_generated",
                     "citizen_understanding_agent", "ai",
                     {"primary_domain": result["dna"]["primary_domain"],
                      "engine": result["dna"].get("ai_source")})
        await ledger(cid, "challenge", "ai_priority_recommended", "priority_engine", "ai",
                     {"score": result["priority"]["score"],
                      "band": result["priority"]["band"]})
        created.append({"challenge_id": cid, "title": result["dna"]["title"],
                        "domain": result["dna"]["primary_domain"],
                        "priority": result["priority"]["score"],
                        "district": rep["district"]})

    return {
        "created": len(created), "challenges": created,
        "ai_mode": groq_client.status()["mode"],
        "next_steps": [
            "POST /api/gov/constellations/detect - find the shared root cause",
            "POST /api/gov/challenges/{id}/review - validate as an officer",
            "GET  /api/gov/challenges/{id}/match - explainable university matching",
            "POST /api/gov/challenges/{id}/coalition - compose the full ecosystem",
            "POST /api/gov/challenges/{id}/allocate - create the project workspace",
        ],
    }


app.include_router(meta)

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def index():
    idx = STATIC_DIR / "index.html"
    if idx.exists():
        return FileResponse(str(idx))
    return {"name": "SAMADHAN GRID", "docs": "/docs"}
