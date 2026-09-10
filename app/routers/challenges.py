"""Citizen engagement layer: submission, evidence, voice, corroboration, feedback."""
from __future__ import annotations

import uuid
from typing import Any

import aiofiles
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from ..config import JHARKHAND_DISTRICTS, UPLOAD_DIR
from ..db import clean, db, ledger, ledger_for, new_id, now
from ..ai import groq_client, priority as prio, similarity, understanding

router = APIRouter(prefix="/api/challenges", tags=["challenges"])

_MEDIA_KIND = {
    "image": {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic"},
    "video": {".mp4", ".mov", ".avi", ".webm", ".mkv"},
    "audio": {".mp3", ".wav", ".m4a", ".ogg", ".webm", ".aac"},
    "document": {".pdf", ".doc", ".docx", ".txt", ".csv", ".xlsx"},
}


def _kind_of(filename: str) -> str:
    ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
    for kind, exts in _MEDIA_KIND.items():
        if ext in exts:
            return kind
    return "document"


class Location(BaseModel):
    district: str
    block: str | None = None
    panchayat_or_ulb: str | None = None
    village_or_ward: str | None = None
    lat: float | None = None
    lon: float | None = None

    def to_doc(self) -> dict[str, Any]:
        d = self.model_dump()
        d["state"] = "Jharkhand"
        if d.get("lat") is None and d["district"] in JHARKHAND_DISTRICTS:
            lat, lon = JHARKHAND_DISTRICTS[d["district"]]
            d["lat"], d["lon"] = lat, lon
            d["coords_source"] = "district_centroid"
        else:
            d["coords_source"] = "gps" if d.get("lat") else "none"
        return d


class SubmitBody(BaseModel):
    text: str = Field(min_length=8)
    language: str = "auto"
    channel: str = "web"          # web | voice | sms | whatsapp | ivr | csc_assisted
    reporter_name: str | None = None
    reporter_contact: str | None = None
    assisted_by: str | None = None
    location: Location
    evidence_ids: list[str] = []


async def _run_pipeline(text: str, language: str, location: dict[str, Any],
                        evidence: list[dict[str, Any]], channel: str,
                        assisted: bool) -> dict[str, Any]:
    """Citizen text -> Problem DNA -> classification -> priority -> dedup."""
    dna = await understanding.build_problem_dna(
        text, language=language, location=location, evidence=evidence)

    # Look for related reports before scoring, so corroboration feeds priority.
    domains = [dna["primary_domain"], *(dna.get("secondary_domains") or [])]
    cursor = db().challenges.find(
        {"status": {"$nin": ["rejected", "draft"]},
         "$or": [{"dna.primary_domain": {"$in": domains}},
                 {"location.district": location.get("district")}]},
        {"_id": 0}).sort("created_at", -1).limit(120)
    candidates = await cursor.to_list(length=120)

    probe = {"dna": dna, "location": location, "created_at": now()}
    related = similarity.find_related(probe, candidates, limit=8)

    dupes = [r for r in related if r["verdict"] == "likely_duplicate"]
    independent = 1 + len(dupes)
    districts = {location.get("district")} | {
        r.get("district") for r in related if r["verdict"] in ("related", "likely_duplicate")}
    districts.discard(None)

    priority = prio.compute_priority(dna, independent_reports=independent,
                                     districts_touched=max(1, len(districts)))
    confidence = prio.evidence_confidence(
        evidence=evidence, location=location, independent_reports=independent,
        text_length=len(text), assisted=assisted, field_verified=False)
    brief = await prio.narrate(dna, priority, confidence)

    return {"dna": dna, "related": related, "priority": priority,
            "evidence_confidence": confidence, "officer_brief": brief,
            "independent_reports": independent}


@router.post("/evidence")
async def upload_evidence(file: UploadFile = File(...)) -> dict[str, Any]:
    """Upload a photo, video, voice note or document before submitting."""
    ext = ("." + file.filename.rsplit(".", 1)[-1].lower()) if "." in (file.filename or "") else ""
    eid = f"EV-{uuid.uuid4().hex[:12]}"
    stored = UPLOAD_DIR / f"{eid}{ext}"
    size = 0
    async with aiofiles.open(stored, "wb") as fh:
        while chunk := await file.read(1 << 20):
            size += len(chunk)
            await fh.write(chunk)
    doc = {"id": eid, "kind": _kind_of(file.filename or ""), "filename": file.filename,
           "stored": stored.name, "url": f"/uploads/{stored.name}",
           "bytes": size, "uploaded_at": now()}
    await db().evidence.insert_one(dict(doc))
    return clean(doc)


@router.post("/transcribe")
async def transcribe(file: UploadFile = File(...),
                     language: str = Form("auto")) -> dict[str, Any]:
    """Voice note -> text, via Groq Whisper. The citizen never has to type."""
    data = await file.read()
    result = await groq_client.transcribe(data, file.filename or "audio.webm",
                                          None if language == "auto" else language)
    if not result:
        raise HTTPException(
            status_code=503,
            detail=("Speech-to-text unavailable. Set GROQ_API_KEY in .env to enable "
                    "voice input, or type the report instead."))
    return {"text": result["text"], "detected_language": result.get("language"),
            "model": groq_client.status()["stt_model"]}


@router.post("")
async def submit(body: SubmitBody) -> dict[str, Any]:
    d = db()
    location = body.location.to_doc()

    evidence: list[dict[str, Any]] = []
    if body.evidence_ids:
        cur = d.evidence.find({"id": {"$in": body.evidence_ids}}, {"_id": 0})
        evidence = await cur.to_list(length=20)

    assisted = body.channel in ("csc_assisted", "helpline", "ivr") or bool(body.assisted_by)
    result = await _run_pipeline(body.text, body.language, location, evidence,
                                 body.channel, assisted)

    cid = new_id("CH")
    doc = {
        "challenge_id": cid,
        "status": "ai_processed",
        "route": None,
        "raw": {"text": body.text, "language": body.language, "channel": body.channel,
                "reporter_name": body.reporter_name, "reporter_contact": body.reporter_contact,
                "assisted_by": body.assisted_by},
        "dna": result["dna"],
        "location": location,
        "evidence": evidence,
        "priority": result["priority"],
        "official_priority": None,
        "evidence_confidence": result["evidence_confidence"],
        "officer_brief": result["officer_brief"],
        "related": result["related"],
        "independent_reports": result["independent_reports"],
        "master_challenge_id": None,
        "corroborates": [],
        "constellation_id": None,
        "project_id": None,
        "review": None,
        "created_at": now(),
        "updated_at": now(),
    }
    await d.challenges.insert_one(dict(doc))

    await ledger(cid, "challenge", "citizen_report_submitted",
                 body.reporter_name or "anonymous_citizen", "citizen",
                 {"channel": body.channel, "language": result["dna"].get("detected_language"),
                  "district": location.get("district")},
                 [e["id"] for e in evidence])
    await ledger(cid, "challenge", "ai_problem_dna_generated", "citizen_understanding_agent",
                 "ai", {"primary_domain": result["dna"]["primary_domain"],
                        "confidence": result["dna"].get("confidence"),
                        "engine": result["dna"].get("ai_source")})
    await ledger(cid, "challenge", "ai_priority_recommended", "priority_engine", "ai",
                 {"score": result["priority"]["score"], "band": result["priority"]["band"],
                  "top_drivers": result["priority"]["top_drivers"]})
    if result["related"]:
        await ledger(cid, "challenge", "ai_related_reports_found", "duplicate_engine", "ai",
                     {"count": len(result["related"]),
                      "likely_duplicates": [r["challenge_id"] for r in result["related"]
                                            if r["verdict"] == "likely_duplicate"]})

    return clean(doc)


@router.get("")
async def list_challenges(status: str | None = None, district: str | None = None,
                          domain: str | None = None, band: str | None = None,
                          reporter: str | None = None, sort: str = "priority",
                          limit: int = 60) -> dict[str, Any]:
    """List reports.

    `sort=recent` puts the newest first - that is what a citizen wants when they
    come back to check on the problem they just sent. `sort=priority` (default)
    puts the most urgent first, which is what an officer wants.
    """
    q: dict[str, Any] = {}
    if status:
        q["status"] = {"$in": status.split(",")}
    if district:
        q["location.district"] = district
    if domain:
        q["$or"] = [{"dna.primary_domain": domain}, {"dna.secondary_domains": domain}]
    if band:
        q["priority.band"] = band
    if reporter:
        q["raw.reporter_name"] = reporter
    key = "created_at" if sort == "recent" else "priority.score"
    cur = db().challenges.find(q, {"_id": 0}).sort(key, -1).limit(limit)
    items = await cur.to_list(length=limit)
    return {"count": len(items), "items": items,
            "total": await db().challenges.count_documents(q)}


# Plain-language status, so a citizen sees progress and not internal jargon.
CITIZEN_STATUS = {
    "draft": ("Not sent yet", "Finish and send your report.", 5),
    "submitted": ("Sent", "Waiting for an officer to look at it.", 20),
    "ai_processed": ("Sent", "Waiting for an officer to look at it.", 20),
    "under_review": ("Being checked", "An officer is reading your report right now.", 35),
    "community_corroborated": ("Others reported it too", "More people confirmed the same problem.", 40),
    "field_verification_required": ("Someone will visit", "An officer will come and see it in person.", 45),
    "field_verified": ("Confirmed on the ground", "An officer visited and confirmed the problem.", 55),
    "validated": ("Approved", "A college or company is being found to solve it.", 65),
    "merged": ("Joined with a bigger report", "Your report made a larger case stronger.", 50),
    "escalated": ("Sent higher up", "Passed to a senior office for a decision.", 50),
    "rejected": ("Closed", "This will be handled another way, not as a project.", 100),
}

PROJECT_STATUS = {
    "problem_validated": ("Team assigned", "A team has taken up your problem.", 70),
    "research_initiated": ("Studying it", "The team is researching the problem.", 74),
    "concept_proposed": ("Plan ready", "The team has proposed a solution.", 78),
    "proof_of_concept": ("Testing the idea", "Checking whether the idea can work.", 80),
    "prototype": ("Building it", "A working version is being made.", 84),
    "lab_testing": ("Testing it", "Being tested before it goes to the village.", 86),
    "field_pilot": ("Trying it in a village", "It is being tested in a real village now.", 90),
    "community_validation": ("Asking the village", "People are being asked if it helped.", 93),
    "production_readiness": ("Getting ready", "Preparing for full use.", 95),
    "deployment": ("In use", "The solution is working in the field.", 97),
    "impact_monitoring": ("Measuring the change", "Checking how much life improved.", 98),
    "scale_up": ("Spreading to more places", "It worked, so it is going to more villages.", 99),
    "completed": ("Finished", "Done and proven.", 100),
}


@router.get("/{challenge_id}/track")
async def track(challenge_id: str) -> dict[str, Any]:
    """Citizen-facing tracking: where is my problem, in plain words?"""
    d = db()
    ch = await d.challenges.find_one({"challenge_id": challenge_id}, {"_id": 0})
    if not ch:
        raise HTTPException(404, "We could not find that reference number.")

    label, detail, pct = CITIZEN_STATUS.get(
        ch.get("status", ""), ("Sent", "Waiting to be looked at.", 20))
    project = None
    if ch.get("project_id"):
        project = await d.projects.find_one({"project_id": ch["project_id"]}, {"_id": 0})
        if project:
            label, detail, pct = PROJECT_STATUS.get(
                project.get("stage", ""), (label, detail, pct))

    feedback = await d.feedback.find({"challenge_id": challenge_id},
                                     {"_id": 0}).to_list(length=50)
    entries = await ledger_for(challenge_id)

    friendly = {
        "citizen_report_submitted": "You sent this report",
        "ai_problem_dna_generated": "The AI read and understood it",
        "ai_priority_recommended": "The AI worked out how urgent it is",
        "ai_related_reports_found": "We found other people reporting the same thing",
        "constellation_detected": "We found the bigger cause behind it",
        "innovation_mission_created": "The government started a mission for it",
        "corroborating_report_linked": "Another report was linked to yours",
        "coalition_proposed": "A team was put together",
        "allocated_to_institution": "Your problem was handed to that team",
        "community_validation_recorded": "Someone from the village gave their verdict",
    }

    channel_name = {
        "web": "the website", "voice": "a voice note", "helpline": "the helpline (8959 491 068)",
        "csc_assisted": "a CSC / Panchayat office", "whatsapp": "WhatsApp",
        "ivr": "an automated phone call", "sms": "SMS",
    }.get(ch.get("raw", {}).get("channel", ""), "the website")

    return {
        "challenge_id": challenge_id,
        "title": ch.get("dna", {}).get("title"),
        "reported_via": channel_name,
        "reported_by": ch.get("raw", {}).get("reporter_name") or "anonymous",
        "reported_at": ch.get("created_at"),
        "place": ", ".join(x for x in [ch.get("location", {}).get("village_or_ward"),
                                       ch.get("location", {}).get("block"),
                                       ch.get("location", {}).get("district")] if x),
        "status_label": label,
        "status_detail": detail,
        "progress_pct": pct,
        "raw_status": ch.get("status"),
        "project_stage": (project or {}).get("stage"),
        "urgency": ch.get("priority", {}).get("band"),
        "also_reported_by": len(ch.get("corroborates") or []),
        "village_verdicts": [{"who": f.get("reporter_name"), "verdict": f.get("verdict"),
                              "comment": f.get("comment")} for f in feedback],
        "history": [{"what": friendly.get(e["event"],
                                          e["event"].replace("_", " ").capitalize()),
                     "who": e["actor"], "role": e["actor_role"], "at": e["at"]}
                    for e in entries],
    }


@router.get("/{challenge_id}")
async def get_challenge(challenge_id: str) -> dict[str, Any]:
    doc = await db().challenges.find_one({"challenge_id": challenge_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Challenge not found")
    doc["ledger"] = await ledger_for(challenge_id)
    doc["feedback"] = await db().feedback.find(
        {"challenge_id": challenge_id}, {"_id": 0}).to_list(length=100)
    if doc.get("project_id"):
        doc["project"] = await db().projects.find_one(
            {"project_id": doc["project_id"]}, {"_id": 0})
    return doc


@router.get("/{challenge_id}/related")
async def related(challenge_id: str) -> dict[str, Any]:
    """Re-run duplicate / constellation detection against the current corpus."""
    d = db()
    doc = await d.challenges.find_one({"challenge_id": challenge_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Challenge not found")
    cur = d.challenges.find(
        {"challenge_id": {"$ne": challenge_id}, "status": {"$nin": ["rejected", "draft"]}},
        {"_id": 0}).limit(200)
    others = await cur.to_list(length=200)
    hits = similarity.find_related(doc, others, limit=12)
    await d.challenges.update_one({"challenge_id": challenge_id},
                                  {"$set": {"related": hits, "updated_at": now()}})
    return {"challenge_id": challenge_id, "related": hits,
            "note": ("Duplicates are never deleted. Each report is preserved as "
                     "independent evidence and linked to a master challenge.")}


class FeedbackBody(BaseModel):
    verdict: str            # fully_resolved | partially_resolved | not_resolved
    rating: int = Field(ge=1, le=5)
    comment: str | None = None
    reporter_name: str | None = None
    evidence_ids: list[str] = []


@router.post("/{challenge_id}/feedback")
async def community_feedback(challenge_id: str, body: FeedbackBody) -> dict[str, Any]:
    """Community validation. The people who reported the problem give the verdict."""
    d = db()
    ch = await d.challenges.find_one({"challenge_id": challenge_id}, {"_id": 0})
    if not ch:
        raise HTTPException(404, "Challenge not found")
    if body.verdict not in ("fully_resolved", "partially_resolved", "not_resolved"):
        raise HTTPException(400, "verdict must be fully_resolved, partially_resolved or not_resolved")

    evidence = []
    if body.evidence_ids:
        evidence = await d.evidence.find({"id": {"$in": body.evidence_ids}},
                                         {"_id": 0}).to_list(length=10)

    doc = {"feedback_id": new_id("FB"), "challenge_id": challenge_id,
           "project_id": ch.get("project_id"), "verdict": body.verdict,
           "rating": body.rating, "comment": body.comment,
           "reporter_name": body.reporter_name or "community member",
           "evidence": evidence, "at": now()}
    await d.feedback.insert_one(dict(doc))

    if ch.get("project_id"):
        await d.projects.update_one({"project_id": ch["project_id"]},
                                    {"$inc": {"community_feedback_count": 1}})

    await ledger(challenge_id, "challenge", "community_validation_recorded",
                 doc["reporter_name"], "citizen",
                 {"verdict": body.verdict, "rating": body.rating},
                 [e["id"] for e in evidence])
    return clean(doc)


@router.get("/{challenge_id}/ledger")
async def get_ledger(challenge_id: str) -> dict[str, Any]:
    entries = await ledger_for(challenge_id)
    return {"challenge_id": challenge_id, "entries": entries,
            "note": "Evidence-to-Impact Ledger: append-only, timestamped, attributable."}
