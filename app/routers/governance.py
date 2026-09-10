"""Government layer: validation workflow, constellations, missions, matching, allocation."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..config import CHALLENGE_STATES, ROUTES
from ..db import clean, db, ledger, new_id, now
from ..ai import coalition as coalition_ai, matching, priority as prio, similarity

router = APIRouter(prefix="/api/gov", tags=["governance"])


class ReviewBody(BaseModel):
    decision: str                    # validated | rejected | field_verification_required |
                                     # field_verified | merged | escalated | community_corroborated
    officer: str
    notes: str | None = None
    route: str | None = None         # grievance | service_delivery | research_challenge | ...
    official_priority: str | None = None   # critical | high | medium | low
    merge_into: str | None = None


@router.get("/queue")
async def review_queue(limit: int = 50, sort: str = "priority") -> dict[str, Any]:
    """Everything awaiting a human decision.

    `sort=priority` (default) is what an officer clearing a backlog wants.
    `sort=recent` is what anyone who just filed a report wants - otherwise a new
    low-urgency report lands at the bottom of a long list and looks lost.
    """
    key = "created_at" if sort == "recent" else "priority.score"
    cur = db().challenges.find(
        {"status": {"$in": ["ai_processed", "submitted", "under_review",
                            "field_verification_required", "community_corroborated"]}},
        {"_id": 0}).sort(key, -1).limit(limit)
    items = await cur.to_list(length=limit)
    return {"count": len(items), "items": items, "sort": sort}


@router.post("/challenges/{challenge_id}/review")
async def review(challenge_id: str, body: ReviewBody) -> dict[str, Any]:
    """Human-in-the-loop gate. AI recommends; an authorised officer decides."""
    d = db()
    ch = await d.challenges.find_one({"challenge_id": challenge_id}, {"_id": 0})
    if not ch:
        raise HTTPException(404, "Challenge not found")
    if body.decision not in CHALLENGE_STATES:
        raise HTTPException(400, f"decision must be one of {CHALLENGE_STATES}")
    if body.route and body.route not in ROUTES:
        raise HTTPException(400, f"route must be one of {ROUTES}")

    update: dict[str, Any] = {
        "status": body.decision,
        "updated_at": now(),
        "review": {"by": body.officer, "at": now(), "decision": body.decision,
                   "notes": body.notes, "route": body.route},
    }
    if body.route:
        update["route"] = body.route
    if body.official_priority:
        update["official_priority"] = {
            "band": body.official_priority, "set_by": body.officer, "at": now(),
            "ai_recommended": ch.get("priority", {}).get("band"),
            "overridden": body.official_priority != ch.get("priority", {}).get("band"),
        }

    if body.decision == "merged":
        if not body.merge_into:
            raise HTTPException(400, "merge_into is required when merging")
        master = await d.challenges.find_one({"challenge_id": body.merge_into}, {"_id": 0})
        if not master:
            raise HTTPException(404, "Master challenge not found")
        update["master_challenge_id"] = body.merge_into
        await d.challenges.update_one(
            {"challenge_id": body.merge_into},
            {"$addToSet": {"corroborates": challenge_id},
             "$inc": {"independent_reports": 1}, "$set": {"updated_at": now()}})
        # Corroboration changes the priority picture of the master challenge.
        fresh = await d.challenges.find_one({"challenge_id": body.merge_into}, {"_id": 0})
        recomputed = prio.compute_priority(
            fresh["dna"], independent_reports=fresh.get("independent_reports", 1),
            districts_touched=1)
        await d.challenges.update_one({"challenge_id": body.merge_into},
                                      {"$set": {"priority": recomputed}})
        await ledger(body.merge_into, "challenge", "corroborating_report_linked",
                     body.officer, "govt_officer",
                     {"from": challenge_id, "new_priority": recomputed["score"]})

    if body.decision == "field_verified":
        conf = prio.evidence_confidence(
            evidence=ch.get("evidence", []), location=ch.get("location", {}),
            independent_reports=ch.get("independent_reports", 1),
            text_length=len(ch.get("raw", {}).get("text", "")),
            assisted=bool(ch.get("raw", {}).get("assisted_by")), field_verified=True)
        update["evidence_confidence"] = conf

    await d.challenges.update_one({"challenge_id": challenge_id}, {"$set": update})
    await ledger(challenge_id, "challenge", f"officer_decision_{body.decision}",
                 body.officer, "govt_officer",
                 {"notes": body.notes, "route": body.route,
                  "official_priority": body.official_priority,
                  "ai_recommended_band": ch.get("priority", {}).get("band")})

    doc = await d.challenges.find_one({"challenge_id": challenge_id}, {"_id": 0})
    return clean(doc)


# --------------------------------------------------------------- constellations

@router.post("/constellations/detect")
async def detect_constellations(district: str | None = None,
                                min_size: int = 3) -> dict[str, Any]:
    """Find groups of different reports that may share one root cause."""
    d = db()
    q: dict[str, Any] = {"status": {"$nin": ["rejected", "draft", "merged"]}}
    if district:
        q["location.district"] = district
    items = await d.challenges.find(q, {"_id": 0}).limit(300).to_list(length=300)

    groups = [g for g in similarity.cluster(items) if len(g) >= min_size]
    out = []
    for g in groups:
        analysis = await similarity.analyse_constellation(g)
        if not analysis.get("is_constellation"):
            continue
        existing = await d.constellations.find_one(
            {"challenge_ids": {"$all": analysis["challenge_ids"][:3]}}, {"_id": 0})
        if existing:
            out.append(existing)
            continue
        doc = {"constellation_id": new_id("CN"), **analysis,
               "status": "detected", "mission_id": None, "created_at": now()}
        await d.constellations.insert_one(dict(doc))
        for cid in analysis["challenge_ids"]:
            await d.challenges.update_one(
                {"challenge_id": cid},
                {"$set": {"constellation_id": doc["constellation_id"]}})
            await ledger(cid, "challenge", "constellation_detected",
                         "constellation_engine", "ai",
                         {"constellation_id": doc["constellation_id"],
                          "root_cause": analysis.get("root_cause_hypothesis")})
        out.append(clean(doc))

    return {"detected": len(out), "constellations": out,
            "note": ("Multiple different local problems may be symptoms of one regional "
                     "root cause. These become candidate Innovation Missions.")}


@router.get("/constellations")
async def list_constellations() -> dict[str, Any]:
    items = await db().constellations.find({}, {"_id": 0}).sort("created_at", -1).to_list(50)
    return {"count": len(items), "items": items}


class MissionBody(BaseModel):
    constellation_id: str
    name: str
    outcome_statement: str
    target_districts: list[str] = []
    duration_months: int = 18
    budget_envelope: float = 0
    created_by: str


@router.post("/missions")
async def create_mission(body: MissionBody) -> dict[str, Any]:
    """Turn a constellation into a funded, outcome-measured Innovation Mission."""
    d = db()
    con = await d.constellations.find_one({"constellation_id": body.constellation_id},
                                          {"_id": 0})
    if not con:
        raise HTTPException(404, "Constellation not found")

    doc = {
        "mission_id": new_id("MS"),
        "constellation_id": body.constellation_id,
        "name": body.name,
        "outcome_statement": body.outcome_statement,
        "root_cause_hypothesis": con.get("root_cause_hypothesis"),
        "target_districts": body.target_districts or con.get("districts", []),
        "challenge_ids": con.get("challenge_ids", []),
        "workstreams": con.get("workstreams", []),
        "duration_months": body.duration_months,
        "budget_envelope": body.budget_envelope,
        "budget_released": 0,
        "projects": [],
        "status": "active",
        "created_by": body.created_by,
        "created_at": now(),
    }
    await d.missions.insert_one(dict(doc))
    await d.constellations.update_one({"constellation_id": body.constellation_id},
                                      {"$set": {"status": "mission_created",
                                                "mission_id": doc["mission_id"]}})
    for cid in doc["challenge_ids"]:
        await ledger(cid, "challenge", "innovation_mission_created", body.created_by,
                     "govt_officer", {"mission_id": doc["mission_id"], "name": body.name,
                                      "outcome": body.outcome_statement})
    return clean(doc)


@router.get("/missions")
async def list_missions() -> dict[str, Any]:
    items = await db().missions.find({}, {"_id": 0}).sort("created_at", -1).to_list(50)
    return {"count": len(items), "items": items}


# ------------------------------------------------------------------- matching

@router.get("/challenges/{challenge_id}/match")
async def match_institutions(challenge_id: str, top_n: int = 5,
                             explain: bool = False) -> dict[str, Any]:
    """Explainable HEI matching over the Innovation Knowledge Graph."""
    d = db()
    ch = await d.challenges.find_one({"challenge_id": challenge_id}, {"_id": 0})
    if not ch:
        raise HTTPException(404, "Challenge not found")

    institutions = await d.institutions.find({}, {"_id": 0}).to_list(length=200)
    ranked = matching.rank_institutions(ch["dna"], ch["location"], institutions, top_n)

    if explain and ranked:
        ranked[0]["official_justification"] = await matching.explain_allocation(
            ch["dna"], ranked[0])

    partners = await d.partners.find({}, {"_id": 0}).to_list(length=200)
    partner_fits = coalition_ai.match_partners(ch["dna"], ch["location"], partners)

    return {
        "challenge_id": challenge_id,
        "required_expertise": ch["dna"].get("required_expertise", []),
        "institutions": ranked,
        "consortium_analysis": matching.consortium_gap(ch["dna"], ranked[:3]),
        "partners": partner_fits[:8],
        "note": ("Every score is a sum of weighted, individually explainable factors. "
                 "The officer allocates; the AI only recommends."),
    }


@router.post("/challenges/{challenge_id}/coalition")
async def compose_coalition(challenge_id: str) -> dict[str, Any]:
    """AI Coalition Composer: the whole ecosystem, not just one university."""
    d = db()
    ch = await d.challenges.find_one({"challenge_id": challenge_id}, {"_id": 0})
    if not ch:
        raise HTTPException(404, "Challenge not found")

    institutions = await d.institutions.find({}, {"_id": 0}).to_list(length=200)
    partners = await d.partners.find({}, {"_id": 0}).to_list(length=200)
    ranked = matching.rank_institutions(ch["dna"], ch["location"], institutions, 4)
    partner_fits = coalition_ai.match_partners(ch["dna"], ch["location"], partners)

    proposal = await coalition_ai.compose(ch["dna"], ch["location"], ranked, partner_fits)
    proposal["coalition_id"] = new_id("CO")
    proposal["challenge_id"] = challenge_id
    proposal["created_at"] = now()
    await d.coalitions.insert_one(dict(proposal))
    await d.challenges.update_one({"challenge_id": challenge_id},
                                  {"$set": {"coalition_id": proposal["coalition_id"]}})
    await ledger(challenge_id, "challenge", "coalition_proposed", "coalition_composer",
                 "ai", {"coalition_id": proposal["coalition_id"],
                        "members": len(proposal.get("members", [])),
                        "lead": proposal.get("lead", {}).get("member")})
    return clean(proposal)


class AllocateBody(BaseModel):
    institution_ids: list[str] = Field(min_length=1)
    partner_ids: list[str] = []
    officer: str
    mode: str = "single"     # single | consortium | invite_proposals | competitive
    justification: str | None = None
    mission_id: str | None = None


@router.post("/challenges/{challenge_id}/allocate")
async def allocate(challenge_id: str, body: AllocateBody) -> dict[str, Any]:
    """Officer allocates the validated challenge and a project workspace is created."""
    d = db()
    ch = await d.challenges.find_one({"challenge_id": challenge_id}, {"_id": 0})
    if not ch:
        raise HTTPException(404, "Challenge not found")
    if ch.get("status") not in ("validated", "field_verified", "community_corroborated"):
        raise HTTPException(
            400, f"Challenge must be validated before allocation (current: {ch.get('status')})")

    insts = await d.institutions.find({"institution_id": {"$in": body.institution_ids}},
                                      {"_id": 0}).to_list(length=10)
    if not insts:
        raise HTTPException(404, "No matching institution found")
    partners = await d.partners.find({"partner_id": {"$in": body.partner_ids}},
                                     {"_id": 0}).to_list(length=10)

    project = {
        "project_id": new_id("PR"),
        "challenge_id": challenge_id,
        "mission_id": body.mission_id,
        "title": ch["dna"]["title"],
        "domain": ch["dna"]["primary_domain"],
        "district": ch["location"].get("district"),
        "location": ch["location"],
        "mode": body.mode,
        "institutions": [{"institution_id": i["institution_id"], "name": i["name"],
                          "lead": i["institution_id"] == body.institution_ids[0]}
                         for i in insts],
        "partners": [{"partner_id": p["partner_id"], "name": p["name"],
                      "type": p["type"]} for p in partners],
        "team": [],
        "stage": "problem_validated",
        "stage_history": [{"stage": "problem_validated", "at": now(), "by": body.officer}],
        "readiness": {"trl": 1, "crl": 2, "srl": 1},
        "impact_contract": {},
        "milestones": [],
        "funding": {"committed": 0, "released": 0, "tranches": []},
        "solution_memory_review": None,
        "impact": {},
        "community_feedback_count": 0,
        "created_by": body.officer,
        "created_at": now(),
        "updated_at": now(),
    }
    await d.projects.insert_one(dict(project))
    await d.challenges.update_one(
        {"challenge_id": challenge_id},
        {"$set": {"project_id": project["project_id"], "status": "validated",
                  "allocation": {"institutions": body.institution_ids,
                                 "partners": body.partner_ids, "mode": body.mode,
                                 "by": body.officer, "at": now(),
                                 "justification": body.justification},
                  "updated_at": now()}})
    if body.mission_id:
        await d.missions.update_one({"mission_id": body.mission_id},
                                    {"$addToSet": {"projects": project["project_id"]}})

    await ledger(challenge_id, "challenge", "allocated_to_institution", body.officer,
                 "govt_officer", {"institutions": [i["name"] for i in insts],
                                  "partners": [p["name"] for p in partners],
                                  "mode": body.mode, "project_id": project["project_id"],
                                  "justification": body.justification})
    await ledger(project["project_id"], "project", "project_workspace_created",
                 body.officer, "govt_officer", {"challenge_id": challenge_id})
    return clean(project)
