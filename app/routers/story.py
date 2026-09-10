"""One real problem, told as six scenes.

Everything here is read out of the database - it is the actual journey of an actual
record, not a scripted narrative. This is the page to show someone who has two
minutes and wants to understand the whole platform.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from ..db import db, ledger_for
from ..ai import impact as impact_ai

router = APIRouter(prefix="/api", tags=["story"])

_ORDER = ["problem_validated", "research_initiated", "concept_proposed", "proof_of_concept",
          "prototype", "lab_testing", "field_pilot", "community_validation",
          "production_readiness", "deployment", "impact_monitoring", "scale_up", "completed"]
_RANK = {s: i for i, s in enumerate(_ORDER)}


@router.get("/story")
async def story() -> dict[str, Any]:
    d = db()
    projects = await d.projects.find({}, {"_id": 0}).to_list(length=500)
    if not projects:
        return {"found": False,
                "message": "No project has started yet. Load the demo, then walk through steps 2 to 6."}

    proj = max(projects, key=lambda p: (_RANK.get(p.get("stage"), 0),
                                        p.get("impact", {}).get("success_rate_pct") or 0))

    ch = await d.challenges.find_one({"challenge_id": proj["challenge_id"]}, {"_id": 0}) or {}
    dna = ch.get("dna", {})
    loc = ch.get("location", {})
    con = await d.constellations.find_one(
        {"challenge_ids": proj["challenge_id"]}, {"_id": 0}) or {}
    mission = await d.missions.find_one({"mission_id": proj.get("mission_id")}, {"_id": 0}) or {}
    coalition = await d.coalitions.find_one({"challenge_id": proj["challenge_id"]},
                                            {"_id": 0}) or {}
    feedback = await d.feedback.find({"challenge_id": proj["challenge_id"]},
                                     {"_id": 0}).to_list(length=100)
    sm = proj.get("solution_memory_review") or {}
    impact = proj.get("impact") or {}
    trail = await ledger_for(proj["challenge_id"])

    place = ", ".join(x for x in [loc.get("village_or_ward"), loc.get("block"),
                                  loc.get("district")] if x)
    people = dna.get("people_affected_estimate")
    ready = impact_ai.readiness_summary(proj.get("readiness", {}).get("trl", 1),
                                        proj.get("readiness", {}).get("crl", 1),
                                        proj.get("readiness", {}).get("srl", 1))

    scenes = [
        {
            "n": 1, "icon": "speak", "title": "Someone speaks up",
            "lead": (f"{ch.get('raw', {}).get('reporter_name') or 'A citizen'} reported a problem "
                     f"from {place or 'their village'}."),
            "quote": ch.get("raw", {}).get("text"),
            "facts": [["Reported through", str(ch.get("raw", {}).get("channel", "")).replace("_", " ")],
                      ["Language used", dna.get("detected_language", "-")],
                      ["Place", place or "-"]],
            "note": "No form to fill in, no department to know. Just what is wrong, in their own words.",
        },
        {
            "n": 2, "icon": "check", "title": "The AI understands it. A human decides.",
            "lead": dna.get("title", ""),
            "body": dna.get("description", ""),
            "facts": [["Type of problem", str(dna.get("primary_domain", "")).replace("_", " ")],
                      ["Who it hurts most", ", ".join(dna.get("vulnerable_groups") or []) or "-"],
                      ["People affected", f"about {people:,}" if people else "not stated"],
                      ["AI suggested", f"{ch.get('priority', {}).get('score')} out of 100 "
                                       f"({ch.get('priority', {}).get('band')})"],
                      ["Officer decided", (ch.get("official_priority") or {}).get("band")
                       or ch.get("status", "-")]],
            "reasons": [f["reason"] for f in ch.get("priority", {}).get("factors", [])][:3],
            "note": "The AI only suggests. An officer made the real call, and it is on the record forever.",
        },
        {
            "n": 3, "icon": "link", "title": "Many small reports, one real cause",
            "lead": (con.get("root_cause_hypothesis")
                     or "No wider pattern was found for this one, so it was handled on its own."),
            "body": con.get("reasoning", ""),
            "facts": [["Separate reports joined", str(con.get("report_count", 1))],
                      ["Districts involved", ", ".join(con.get("districts") or []) or "-"],
                      ["Mission started", mission.get("name") or "not yet"],
                      ["Goal agreed", mission.get("outcome_statement") or "-"]],
            "note": "Fixing one handpump helps one village. Fixing the cause helps forty.",
        },
        {
            "n": 4, "icon": "team", "title": "The right people are chosen",
            "lead": (f"{coalition.get('coalition_name') or 'A team'} was put together, led by "
                     f"{(coalition.get('lead') or {}).get('member') or 'the lead college'}."),
            "members": [{"name": m.get("name"), "kind": m.get("kind"), "role": m.get("role")}
                        for m in (coalition.get("members") or [])][:8],
            "facts": [["Colleges", ", ".join(i["name"] for i in proj.get("institutions", []))],
                      ["Partners", ", ".join(p["name"] for p in proj.get("partners", [])) or "-"],
                      ["Skills needed", ", ".join(dna.get("required_expertise") or [])],
                      ["People on the team", str(len(proj.get("team", [])))]],
            "note": "Chosen on what they can actually do, not on who was nearest. Every score was explained.",
        },
        {
            "n": 5, "icon": "build", "title": "Old mistakes avoided, then it is built",
            "lead": sm.get("headline") or "The team checked what already existed before building anything.",
            "failures": [{"title": f.get("title"), "why": f.get("what_went_wrong"),
                          "lesson": f.get("how_to_avoid")}
                         for f in (sm.get("failure_warnings") or [])],
            "facts": [["Past work searched", str(sm.get("searched", 0))],
                      ["Failures surfaced", str(sm.get("failures_found", 0))],
                      ["Decision", str(sm.get("verdict", "-")).replace("_", " ")],
                      ["Money released", f"{proj.get('funding', {}).get('released', 0):,.0f}"],
                      ["Proof files uploaded", str(sum(len(m.get("evidence") or [])
                                                       for m in proj.get("milestones", [])))]],
            "note": "No step counts as done without an uploaded file. Money only moves after proof.",
        },
        {
            "n": 6, "icon": "proof", "title": "Did life actually get better?",
            "lead": ("The village said yes."
                     if any(f.get("verdict") == "fully_resolved" for f in feedback)
                     else "The village has not given its verdict yet."),
            "rows": impact.get("rows", []),
            "village": [{"who": f.get("reporter_name"), "verdict": f.get("verdict"),
                         "rating": f.get("rating"), "comment": f.get("comment")}
                        for f in feedback],
            "facts": [["Promises kept", f"{impact.get('success_rate_pct', 0)}%"],
                      ["People helped", f"{impact.get('beneficiaries', 0):,}"],
                      ["Cost per person", f"{impact.get('cost_per_beneficiary'):,.0f}"
                       if impact.get("cost_per_beneficiary") else "-"],
                      ["Ready to spread?", "yes" if ready["scale_ready"] else "not yet"]],
            "note": "The people who reported the problem give the final verdict. Nobody else can.",
        },
    ]

    return {
        "found": True,
        "challenge_id": proj["challenge_id"],
        "project_id": proj["project_id"],
        "title": proj.get("title"),
        "place": place,
        "stage": proj.get("stage"),
        "scenes": scenes,
        "trail": [{"event": e["event"].replace("_", " "), "who": e["actor"],
                   "role": e["actor_role"], "at": e["at"]} for e in trail],
    }
