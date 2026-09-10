"""Solution Memory & Reuse Engine + Failure Intelligence.

Before a team is allowed to invent anything, we search what already exists:
completed Jharkhand projects, national initiatives, university prototypes, papers,
patents, startup products, open-source work, government schemes and international
cases - plus, crucially, the things that were TRIED AND FAILED and why.

Failure is treated as an asset, not something to hide.
"""
from __future__ import annotations

from typing import Any

from . import groq_client, similarity

_CLASSES = {
    "reusable": "Can be used almost as-is. Deploy, do not rebuild.",
    "adaptable": "Right idea, wrong context. Adapt it to local conditions.",
    "partnership": "Someone already owns this. Partner instead of competing.",
    "research": "Useful knowledge, not a product. Read before designing.",
    "ip_risk": "Patented or licensed. Check freedom to operate before building.",
    "failure": "This was tried and did not work. Learn the lesson first.",
}


def _classify(item: dict[str, Any], score: float) -> str:
    if item.get("kind") == "failure":
        return "failure"
    if item.get("patented") or item.get("kind") == "patent":
        return "ip_risk"
    if item.get("kind") in ("paper", "research"):
        return "research"
    if item.get("kind") in ("startup_product", "commercial"):
        return "partnership"
    if score >= 0.55 and item.get("maturity") in ("deployed", "scaled"):
        return "reusable"
    return "adaptable"


def search(dna: dict[str, Any], library: list[dict[str, Any]],
           limit: int = 8) -> list[dict[str, Any]]:
    """Rank the knowledge library against this problem."""
    if not library:
        return []
    query = similarity.text_of(dna)
    texts = [
        " ".join(filter(None, [
            it.get("title", ""), it.get("summary", ""),
            " ".join(it.get("tags") or []),
            str(it.get("domain", "")).replace("_", " "),
            " ".join(it.get("technologies") or []),
        ])) for it in library
    ]
    sims = similarity.cosine(query, texts)

    domains = {dna.get("primary_domain"), *(dna.get("secondary_domains") or [])}
    results: list[dict[str, Any]] = []
    for item, sim in zip(library, sims):
        boost = 0.18 if item.get("domain") in domains else 0.0
        score = round(min(1.0, sim + boost), 4)
        if score < 0.12:
            continue
        klass = _classify(item, score)
        results.append({
            "solution_id": item.get("solution_id"),
            "title": item.get("title"),
            "kind": item.get("kind"),
            "source": item.get("source"),
            "year": item.get("year"),
            "domain": item.get("domain"),
            "summary": item.get("summary"),
            "technologies": item.get("technologies") or [],
            "maturity": item.get("maturity"),
            "url": item.get("url"),
            "relevance": score,
            "classification": klass,
            "classification_note": _CLASSES[klass],
            "failure_reason": item.get("failure_reason"),
            "lesson": item.get("lesson"),
            "cost_note": item.get("cost_note"),
        })

    results.sort(key=lambda r: (r["classification"] != "failure", -r["relevance"]))
    return results[:limit]


ADVICE_SYSTEM = """You are the Solution Memory Engine of SAMADHAN GRID.

A student/faculty team is about to start building a solution. You have searched the
knowledge base. Your job is to stop them wasting a year rebuilding something that
already exists, or repeating a failure someone already paid for.

Be blunt and specific. If a past attempt failed, lead with that. Cite the items by
title. Never invent sources that were not given to you.

Return ONLY JSON:
{
  "verdict": "reuse | adapt | partner | build_new",
  "headline": "one sentence telling the team what to do",
  "reasoning": "3-4 sentences citing the specific items by title",
  "must_read": ["titles the team must read before designing"],
  "failure_warnings": [
     {"title": "...", "what_went_wrong": "...", "how_to_avoid": "..."}
  ],
  "design_constraints": ["hard constraints this context imposes, e.g. maintenance cost"],
  "reuse_candidates": ["titles worth reusing or adapting"],
  "estimated_time_saved_months": integer
}"""


async def advise(dna: dict[str, Any], hits: list[dict[str, Any]]) -> dict[str, Any]:
    failures = [h for h in hits if h["classification"] == "failure"]
    reusables = [h for h in hits if h["classification"] in ("reusable", "adaptable")]

    listing = "\n".join(
        f"- [{h['classification']}] \"{h['title']}\" ({h.get('source')}, {h.get('year')}), "
        f"relevance {h['relevance']}, maturity {h.get('maturity')}. {h.get('summary')}"
        + (f" FAILED BECAUSE: {h['failure_reason']}. LESSON: {h.get('lesson')}"
           if h.get("failure_reason") else "")
        for h in hits) or "- nothing found in the knowledge base"

    user = (f"Problem: {dna.get('title')}\n"
            f"Context: {dna.get('description')}\n"
            f"Domain: {dna.get('primary_domain')}\n"
            f"Location context: rural Jharkhand, low maintenance capacity, "
            f"intermittent power and connectivity\n\n"
            f"Knowledge base hits:\n{listing}\n\nAdvise the team now.")

    raw = await groq_client.json_call(ADVICE_SYSTEM, user, temperature=0.25)

    if not raw:
        verdict = ("adapt" if reusables else "build_new")
        raw = {
            "verdict": verdict,
            "headline": (
                f"{len(failures)} past attempt(s) failed here - read them before designing."
                if failures else
                f"{len(reusables)} existing solution(s) look adaptable; do not start from zero."
                if reusables else
                "No close prior art found. A genuinely new build appears justified."),
            "reasoning": "Ranked by semantic similarity to the Problem DNA and domain match.",
            "must_read": [h["title"] for h in hits[:3]],
            "failure_warnings": [
                {"title": f["title"], "what_went_wrong": f.get("failure_reason", ""),
                 "how_to_avoid": f.get("lesson", "")} for f in failures],
            "design_constraints": [
                "Must survive with village-level maintenance skills",
                "Must tolerate power and network outages",
            ],
            "reuse_candidates": [h["title"] for h in reusables[:3]],
            "estimated_time_saved_months": 3 * len(reusables),
        }

    raw["hits"] = hits
    raw["searched"] = len(hits)
    raw["failures_found"] = len(failures)
    raw["source"] = "groq" if groq_client.available() else "fallback"
    return raw
