"""Society satisfaction: how are we treating the people who use this?

This is deliberately separate from the per-project community verdict in
challenges.py. That one asks "did this project fix your problem?". This one asks
"was the service itself any good?" - was reporting easy, did anyone tell you what
happened, would you tell a neighbour to use it.

A platform can close every project and still be failing the people it serves.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..db import clean, db, ledger, new_id, now
from ..ai import groq_client

router = APIRouter(prefix="/api/satisfaction", tags=["satisfaction"])

# The four things that decide whether a citizen trusts this service again.
QUESTIONS = [
    {"key": "easy_to_report", "q": "Was it easy to report your problem?",
     "low": "Very hard", "high": "Very easy"},
    {"key": "got_updates", "q": "Were you told what was happening with it?",
     "low": "Heard nothing", "high": "Kept well informed"},
    {"key": "problem_solved", "q": "Did your problem actually get solved?",
     "low": "Not at all", "high": "Completely"},
    {"key": "treated_fairly", "q": "Were you treated with respect?",
     "low": "Not at all", "high": "Completely"},
]

WHO = ["citizen", "student", "teacher", "government officer", "company or NGO", "other"]


class ReviewBody(BaseModel):
    overall: int = Field(ge=1, le=5)
    easy_to_report: int | None = Field(default=None, ge=1, le=5)
    got_updates: int | None = Field(default=None, ge=1, le=5)
    problem_solved: int | None = Field(default=None, ge=1, le=5)
    treated_fairly: int | None = Field(default=None, ge=1, le=5)
    would_recommend: bool | None = None
    comment: str | None = None
    name: str | None = None
    district: str | None = None
    who: str = "citizen"
    challenge_id: str | None = None


@router.post("")
async def leave_review(body: ReviewBody) -> dict[str, Any]:
    d = db()
    if body.challenge_id:
        exists = await d.challenges.find_one({"challenge_id": body.challenge_id},
                                             {"_id": 0, "challenge_id": 1})
        if not exists:
            raise HTTPException(404, "We could not find that reference number.")

    doc = {
        "review_id": new_id("RV"),
        "overall": body.overall,
        "scores": {q["key"]: getattr(body, q["key"]) for q in QUESTIONS},
        "would_recommend": body.would_recommend,
        "comment": (body.comment or "").strip() or None,
        "name": (body.name or "").strip() or "Anonymous",
        "district": body.district,
        "who": body.who,
        "challenge_id": body.challenge_id,
        "at": now(),
    }
    await d.reviews.insert_one(dict(doc))
    await ledger(body.challenge_id or "platform", "satisfaction", "service_review_left",
                 doc["name"], "citizen",
                 {"overall": body.overall, "would_recommend": body.would_recommend})
    return clean(doc)


def _avg(values: list[int]) -> float | None:
    vals = [v for v in values if isinstance(v, int)]
    return round(sum(vals) / len(vals), 2) if vals else None


@router.get("")
async def satisfaction(limit: int = 40) -> dict[str, Any]:
    """Everything the UI needs: the score, the spread, and what people actually said."""
    reviews = await db().reviews.find({}, {"_id": 0}).sort("at", -1).to_list(length=2000)

    if not reviews:
        return {"count": 0, "average": None, "distribution": [], "questions": QUESTIONS,
                "recent": [], "message": "Nobody has reviewed the service yet."}

    overall = [r["overall"] for r in reviews]
    dist = Counter(overall)
    total = len(reviews)

    recommend = [r["would_recommend"] for r in reviews if r["would_recommend"] is not None]
    happy = sum(1 for v in overall if v >= 4)
    unhappy = sum(1 for v in overall if v <= 2)

    per_question = []
    for q in QUESTIONS:
        vals = [r.get("scores", {}).get(q["key"]) for r in reviews]
        per_question.append({**q, "average": _avg(vals),
                             "answers": len([v for v in vals if isinstance(v, int)])})

    return {
        "count": total,
        "average": round(sum(overall) / total, 2),
        "distribution": [{"stars": s, "count": dist.get(s, 0),
                          "pct": round(100 * dist.get(s, 0) / total, 1)}
                         for s in (5, 4, 3, 2, 1)],
        "happy_pct": round(100 * happy / total, 1),
        "unhappy_pct": round(100 * unhappy / total, 1),
        "recommend_pct": (round(100 * sum(1 for v in recommend if v) / len(recommend), 1)
                          if recommend else None),
        "questions": per_question,
        "by_who": [{"who": k, "count": v} for k, v in Counter(
            r.get("who", "citizen") for r in reviews).most_common()],
        "by_district": [{"district": k, "count": v, "average": _avg(
            [r["overall"] for r in reviews if r.get("district") == k])}
            for k, v in Counter(r.get("district") for r in reviews if r.get("district")
                                ).most_common(8)],
        "recent": [{"review_id": r["review_id"], "overall": r["overall"],
                    "comment": r.get("comment"), "name": r.get("name"),
                    "who": r.get("who"), "district": r.get("district"),
                    "would_recommend": r.get("would_recommend"), "at": r["at"]}
                   for r in reviews[:limit]],
    }


THEMES_SYSTEM = """You read what citizens said about a government service in Jharkhand
and report back honestly to the officials who run it.

Rules:
- Do not soften bad feedback. If people are angry about something, say so plainly.
- Quote or closely paraphrase real comments; invent nothing.
- Praise and complaints are equally important. Report both.
- If there are too few comments to be sure, say so.
- Plain English, short sentences.

Return ONLY JSON:
{
  "headline": "one honest sentence summarising how people feel",
  "working_well": [{"theme":"...", "evidence":"what people said", "mentions": integer}],
  "needs_fixing": [{"theme":"...", "evidence":"what people said", "mentions": integer,
                    "suggested_action":"one concrete thing the state should change"}],
  "most_urgent_fix": "the single change that would help most people",
  "confidence": "high|medium|low"
}"""


@router.get("/themes")
async def themes() -> dict[str, Any]:
    """What are people actually telling us? Grouped into praise and complaints."""
    reviews = await db().reviews.find({"comment": {"$ne": None}},
                                      {"_id": 0}).sort("at", -1).to_list(length=300)
    if len(reviews) < 3:
        return {"enough_data": False,
                "message": f"Only {len(reviews)} written comment(s) so far. "
                           "We need a few more before drawing any conclusion.",
                "comments_read": len(reviews)}

    lines = "\n".join(
        f'- [{r["overall"]}/5, {r.get("who", "citizen")}'
        f'{", " + r["district"] if r.get("district") else ""}] "{r["comment"]}"'
        for r in reviews)

    raw = await groq_client.json_call(
        THEMES_SYSTEM,
        f"{len(reviews)} written comments about the SAMADHAN GRID service:\n{lines}\n\n"
        "Summarise honestly.", temperature=0.25)

    if not raw:
        good = [r for r in reviews if r["overall"] >= 4]
        bad = [r for r in reviews if r["overall"] <= 2]
        raw = {
            "headline": f"{len(good)} of {len(reviews)} people who wrote a comment rated the "
                        f"service 4 or 5 out of 5.",
            "working_well": [{"theme": "Positive comments", "mentions": len(good),
                              "evidence": good[0]["comment"] if good else ""}],
            "needs_fixing": [{"theme": "Negative comments", "mentions": len(bad),
                              "evidence": bad[0]["comment"] if bad else "",
                              "suggested_action": "Read these comments directly."}],
            "most_urgent_fix": "Review the low-rated comments individually.",
            "confidence": "low",
        }
    raw["enough_data"] = True
    raw["comments_read"] = len(reviews)
    raw["source"] = "groq" if groq_client.available() else "fallback"
    return raw
