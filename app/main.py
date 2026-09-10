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
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from . import seed as seed_mod
from .ai import groq_client
from .config import STATIC_DIR, UPLOAD_DIR
from .db import close, connect, db, ledger, new_id
from .routers import analytics, challenges, governance, projects, satisfaction, story

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s - %(message)s")
log = logging.getLogger("samadhan")


# If startup fails we keep serving, so the operator can read WHY at /api/health
# instead of getting an opaque 500 from the platform.
STARTUP_ERROR: dict[str, Any] | None = None


def _diagnose(exc: Exception) -> dict[str, Any]:
    """Turn a database exception into something a human can act on."""
    name = type(exc).__name__
    text = str(exc)
    uri = os.getenv("MONGODB_URI", "")
    if not uri:
        cause, fix = ("MONGODB_URI is not set",
                      "Add MONGODB_URI to your hosting platform's environment variables.")
    elif "localhost" in uri or "127.0.0.1" in uri:
        cause, fix = ("MONGODB_URI still points at localhost",
                      "A hosted app cannot reach your laptop. Use a MongoDB Atlas "
                      "connection string (mongodb+srv://...).")
    elif "ServerSelectionTimeout" in name or "No servers found" in text:
        cause, fix = ("Cannot reach the MongoDB server",
                      "In MongoDB Atlas open Network Access and allow 0.0.0.0/0. "
                      "Serverless hosts have no fixed IP, so an IP allow-list blocks them.")
    elif "Authentication failed" in text or "auth" in text.lower():
        cause, fix = ("MongoDB rejected the username or password",
                      "Check the user in Atlas > Database Access, and make sure you "
                      "replaced <password> in the connection string with the real password. "
                      "If the password has special characters they must be URL-encoded.")
    else:
        cause, fix = (f"Database error: {name}", "Check the connection string and Atlas settings.")
    return {"cause": cause, "fix": fix, "detail": text[:400],
            "mongodb_uri_set": bool(uri),
            "mongodb_uri_host": uri.split("@")[-1].split("/")[0] if "@" in uri else None}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global STARTUP_ERROR
    try:
        await connect()
        counts = await seed_mod.seed_reference_data()
        log.info("Connected to MongoDB. Reference data: %s", counts)
    except Exception as exc:  # noqa: BLE001 - never crash the whole app on a bad DB
        STARTUP_ERROR = _diagnose(exc)
        log.error("DATABASE UNAVAILABLE - %s | Fix: %s",
                  STARTUP_ERROR["cause"], STARTUP_ERROR["fix"])
        log.error("The site will load but show a setup page until this is fixed.")

    try:
        await groq_client.resolve_model()
        log.info("AI mode: %s (chat=%s, stt=%s)", groq_client.status()["mode"],
                 groq_client.active_model(), groq_client.status()["stt_model"])
    except Exception as exc:  # noqa: BLE001
        log.warning("Groq unavailable, falling back to rule-based AI: %s", exc)

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
        mongo = f"error: {type(exc).__name__}"
    out: dict[str, Any] = {
        "status": "ok" if mongo == "connected" else "degraded",
        "mongodb": mongo,
        "ai": groq_client.status(),
    }
    if STARTUP_ERROR:
        out["setup_problem"] = STARTUP_ERROR
    return out


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

if UPLOAD_DIR.exists():
    app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


SETUP_PAGE = """<!doctype html><meta charset="utf-8">
<title>SAMADHAN GRID - setup needed</title>
<style>
 body{{font:16px/1.6 system-ui,sans-serif;background:#f4f7fb;color:#3d4d61;margin:0;padding:40px 20px}}
 .b{{max-width:680px;margin:0 auto;background:#fff;border:1px solid #dfe6ef;border-radius:16px;padding:32px}}
 h1{{color:#132132;font-size:24px;margin:0 0 6px}}
 .t{{display:inline-block;background:#fdecea;color:#b23a34;padding:4px 12px;border-radius:20px;
     font-size:12px;font-weight:700;margin-bottom:16px}}
 .c{{background:#fdf3e3;border-left:4px solid #b9740d;padding:16px;border-radius:0 10px 10px 0;margin:18px 0}}
 .f{{background:#e8f4ea;border-left:4px solid #2f7a45;padding:16px;border-radius:0 10px 10px 0;margin:18px 0}}
 code{{background:#eef2f7;padding:2px 7px;border-radius:5px;font-size:14px}}
 .m{{color:#71829a;font-size:13px;margin-top:22px}}
</style>
<div class="b">
 <div class="t">SETUP NEEDED</div>
 <h1>The app is running, but it cannot reach its database.</h1>
 <p>Everything else is fine - this is a configuration step, not a broken build.</p>
 <div class="c"><b>What is wrong</b><br>{cause}</div>
 <div class="f"><b>How to fix it</b><br>{fix}</div>
 <p class="m">Technical detail: <code>{detail}</code><br>
 Full status at <a href="/api/health">/api/health</a>. This page disappears once the
 database connects.</p>
</div>"""


@app.get("/", include_in_schema=False)
async def index():
    if STARTUP_ERROR:
        return HTMLResponse(SETUP_PAGE.format(
            cause=STARTUP_ERROR["cause"], fix=STARTUP_ERROR["fix"],
            detail=STARTUP_ERROR["detail"][:200]), status_code=503)
    idx = STATIC_DIR / "index.html"
    if idx.exists():
        return FileResponse(str(idx))
    return {"name": "SAMADHAN GRID", "docs": "/docs"}
