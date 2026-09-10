"""Duplicate & Problem Constellation Engine.

Two different jobs:

1. Duplicate detection - "handpump not working", "no drinking water" and "women walk
   3 km to fetch water" are the SAME problem described three ways. We link them as
   corroborating evidence; we never delete a citizen's report.

2. Problem Constellation - drinking water shortage + borewell failure + falling
   groundwater + irrigation failure across nearby villages are DIFFERENT problems
   that may share one root cause. That pattern becomes a district Innovation Mission.
"""
from __future__ import annotations

import math
import re
import zlib
from datetime import datetime, timezone
from typing import Any

import numpy as np

from . import groq_client

# ---------------------------------------------------------------- vectoriser
# A hashing vectoriser in ~30 lines of numpy, replacing scikit-learn + scipy.
# Stateless by design: nothing is "fitted", so a vector computed today still
# matches one computed after a thousand more reports arrive.
#
# Word n-grams catch shared vocabulary. Character n-grams catch spelling
# variants, inflections and transliteration ("handpump" / "hand pump" /
# "chapakal"). Devanagari and other Indian scripts are matched by the same
# unicode-aware word rule.

DIM = 4096                      # 16 KB per document as float32

_WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)

# Only the most common English function words: anything more aggressive starts
# throwing away signal in Hinglish text.
_STOP = {
    "a", "an", "the", "and", "or", "but", "if", "of", "at", "by", "for", "with",
    "to", "from", "in", "on", "is", "are", "was", "were", "be", "been", "it",
    "its", "this", "that", "these", "those", "as", "we", "our", "they", "their",
    "there", "has", "have", "had", "not", "no", "do", "does", "did", "so",
}


def _words(text: str) -> list[str]:
    return [w for w in _WORD_RE.findall(text.lower()) if w not in _STOP]


def _word_grams(text: str) -> list[str]:
    ws = _words(text)
    return ws + [f"{ws[i]} {ws[i + 1]}" for i in range(len(ws) - 1)]


def _char_grams(text: str, lo: int = 3, hi: int = 5) -> list[str]:
    """Character n-grams inside word boundaries, like sklearn's char_wb."""
    out: list[str] = []
    for w in _WORD_RE.findall(text.lower()):
        padded = f" {w} "
        for n in range(lo, hi + 1):
            if len(padded) >= n:
                out.extend(padded[i:i + n] for i in range(len(padded) - n + 1))
    return out


def _accumulate(row: np.ndarray, tokens: list[str], weight: float) -> None:
    # crc32 is deterministic across processes and runs, unlike Python's hash().
    for tok in tokens:
        row[zlib.crc32(tok.encode("utf-8")) % DIM] += weight

# Domains that commonly share a root cause with each other.
_ROOT_CAUSE_FAMILIES = [
    {"water_resources", "agriculture", "environment", "healthcare", "women_child_welfare"},
    {"sanitation", "waste_management", "healthcare", "environment"},
    {"education", "digital_governance", "transportation", "women_child_welfare"},
    {"energy", "healthcare", "education", "rural_livelihood"},
    {"disaster_resilience", "agriculture", "water_resources", "transportation"},
    {"employment", "rural_livelihood", "social_inclusion", "agriculture"},
]


def text_of(dna: dict[str, Any]) -> str:
    parts = [
        dna.get("title", ""), dna.get("description", ""), dna.get("subdomain", ""),
        dna.get("primary_domain", "").replace("_", " "),
        " ".join(dna.get("secondary_domains") or []).replace("_", " "),
        " ".join(dna.get("keywords") or []),
        " ".join(dna.get("suspected_causes") or []),
        dna.get("affected_community", ""),
    ]
    return " ".join(p for p in parts if p).strip()


def embed(texts: list[str]) -> np.ndarray | None:
    """L2-normalised dense embedding matrix for a list of texts."""
    if not texts:
        return None
    m = np.zeros((len(texts), DIM), dtype=np.float32)
    for i, text in enumerate(texts):
        _accumulate(m[i], _word_grams(text), 1.0)
        _accumulate(m[i], _char_grams(text), 0.6)
    norms = np.linalg.norm(m, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return m / norms


def cosine(a_text: str, b_texts: list[str]) -> list[float]:
    if not b_texts:
        return []
    mat = embed([a_text] + b_texts)
    sims = mat[1:] @ mat[0]
    return [float(max(0.0, min(1.0, s))) for s in sims]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _geo_score(a: dict, b: dict) -> tuple[float, str]:
    la, lb = a.get("location", {}), b.get("location", {})
    if la.get("lat") and lb.get("lat"):
        km = haversine_km(la["lat"], la["lon"], lb["lat"], lb["lon"])
        if km <= 2:
            return 1.0, f"Same locality ({km:.1f} km apart)."
        if km <= 10:
            return 0.85, f"Neighbouring villages ({km:.1f} km apart)."
        if km <= 30:
            return 0.6, f"Same block area ({km:.1f} km apart)."
        if km <= 80:
            return 0.35, f"Same district region ({km:.0f} km apart)."
        return 0.1, f"Far apart ({km:.0f} km)."
    if la.get("village_or_ward") and la.get("village_or_ward") == lb.get("village_or_ward"):
        return 0.95, "Same village / ward."
    if la.get("block") and la.get("block") == lb.get("block"):
        return 0.7, "Same block."
    if la.get("district") and la.get("district") == lb.get("district"):
        return 0.45, "Same district."
    return 0.05, "Different district."


def _domain_score(a: dict, b: dict) -> tuple[float, str]:
    da, db = a.get("dna", {}), b.get("dna", {})
    sa = {da.get("primary_domain")} | set(da.get("secondary_domains") or [])
    sb = {db.get("primary_domain")} | set(db.get("secondary_domains") or [])
    sa.discard(None); sb.discard(None)
    if da.get("primary_domain") == db.get("primary_domain"):
        return 1.0, f"Same primary domain ({da.get('primary_domain')})."
    overlap = sa & sb
    if overlap:
        return 0.6, f"Overlapping domains: {', '.join(sorted(overlap))}."
    for fam in _ROOT_CAUSE_FAMILIES:
        if sa & fam and sb & fam:
            return 0.35, "Domains often share a root cause."
    return 0.0, "Unrelated domains."


def _time_score(a: dict, b: dict) -> tuple[float, str]:
    ta, tb = a.get("created_at"), b.get("created_at")
    if not (isinstance(ta, datetime) and isinstance(tb, datetime)):
        return 0.5, "Timing unknown."
    if ta.tzinfo is None:
        ta = ta.replace(tzinfo=timezone.utc)
    if tb.tzinfo is None:
        tb = tb.replace(tzinfo=timezone.utc)
    days = abs((ta - tb).days)
    if days <= 14:
        return 1.0, f"Reported within {days} days of each other."
    if days <= 60:
        return 0.7, f"Reported {days} days apart - same season."
    if days <= 180:
        return 0.4, f"Reported {days} days apart."
    return 0.15, f"Reported {days} days apart - different period."


def relate(new_doc: dict[str, Any], other: dict[str, Any],
           semantic: float) -> dict[str, Any]:
    """Explainable relatedness between two challenges."""
    geo, geo_why = _geo_score(new_doc, other)
    dom, dom_why = _domain_score(new_doc, other)
    tim, tim_why = _time_score(new_doc, other)

    ka = set(k.lower() for k in (new_doc.get("dna", {}).get("keywords") or []))
    kb = set(k.lower() for k in (other.get("dna", {}).get("keywords") or []))
    kw = len(ka & kb) / max(1, len(ka | kb)) if (ka or kb) else 0.0

    score = (0.42 * semantic + 0.22 * geo + 0.16 * dom + 0.10 * tim + 0.10 * kw)
    score = round(float(score), 4)

    if score >= 0.72:
        verdict = "likely_duplicate"
    elif score >= 0.52:
        verdict = "related"
    elif score >= 0.34:
        verdict = "possible_constellation"
    else:
        verdict = "unrelated"

    return {
        "challenge_id": other.get("challenge_id"),
        "title": other.get("dna", {}).get("title"),
        "district": other.get("location", {}).get("district"),
        "status": other.get("status"),
        "score": score,
        "verdict": verdict,
        "breakdown": [
            {"signal": "Semantic meaning", "value": round(semantic, 3), "weight": 0.42,
             "reason": "Wording differs but meaning overlaps."
                       if semantic > 0.3 else "Little textual overlap."},
            {"signal": "Geographic proximity", "value": round(geo, 3), "weight": 0.22,
             "reason": geo_why},
            {"signal": "Domain relationship", "value": round(dom, 3), "weight": 0.16,
             "reason": dom_why},
            {"signal": "Time proximity", "value": round(tim, 3), "weight": 0.10,
             "reason": tim_why},
            {"signal": "Keyword overlap", "value": round(kw, 3), "weight": 0.10,
             "reason": f"{len(ka & kb)} shared keyword(s)."},
        ],
    }


def find_related(new_doc: dict[str, Any], candidates: list[dict[str, Any]],
                 limit: int = 8) -> list[dict[str, Any]]:
    if not candidates:
        return []
    base = text_of(new_doc.get("dna", {}))
    others = [text_of(c.get("dna", {})) for c in candidates]
    sims = cosine(base, others)
    out = [relate(new_doc, c, s) for c, s in zip(candidates, sims)]
    out = [o for o in out if o["verdict"] != "unrelated"]
    out.sort(key=lambda o: -o["score"])
    return out[:limit]


# ------------------------------------------------------------- constellations

def cluster(challenges: list[dict[str, Any]], threshold: float = 0.34
            ) -> list[list[dict[str, Any]]]:
    """Connected-component clustering over the relatedness graph."""
    n = len(challenges)
    if n < 2:
        return []
    texts = [text_of(c.get("dna", {})) for c in challenges]
    mat = embed(texts)
    sim = mat @ mat.T

    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[rj] = ri

    for i in range(n):
        for j in range(i + 1, n):
            r = relate(challenges[i], challenges[j], float(sim[i][j]))
            if r["score"] >= threshold:
                union(i, j)

    groups: dict[int, list[dict[str, Any]]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(challenges[i])
    return [g for g in groups.values() if len(g) >= 3]


CONSTELLATION_SYSTEM = """You are the Problem Constellation Engine of SAMADHAN GRID
(Government of Jharkhand).

You are shown several DIFFERENT citizen-reported problems from nearby areas. Your job
is to judge whether they are separate issues, or symptoms of ONE deeper root cause that
the state should attack as a single Innovation Mission.

Be honest. If they are genuinely unrelated, say so with low confidence. Do not force a
pattern. Ground every claim in the reports you were given.

Return ONLY JSON:
{
  "is_constellation": true/false,
  "root_cause_hypothesis": "one clear sentence naming the suspected shared root cause",
  "reasoning": "3-4 sentences explaining how these symptoms connect",
  "confidence": 0.0-1.0,
  "mission_name": "short name for a district innovation mission, max 60 chars",
  "mission_outcome": "ONE measurable outcome statement with a number and a timeframe",
  "workstreams": [
     {"name": "component name", "why": "what this component solves",
      "expertise": ["disciplines needed"]}
  ],
  "evidence_gaps": ["what data the government should collect to confirm this"]
}"""


async def analyse_constellation(group: list[dict[str, Any]]) -> dict[str, Any]:
    """Ask the LLM whether a cluster is really one root cause, and shape the mission."""
    lines = []
    districts, domains = set(), set()
    for c in group:
        d = c.get("dna", {})
        loc = c.get("location", {})
        districts.add(loc.get("district"))
        domains.add(d.get("primary_domain"))
        lines.append(
            f"- [{d.get('primary_domain')}] {d.get('title')} "
            f"({loc.get('village_or_ward') or '-'}, {loc.get('block') or '-'}, "
            f"{loc.get('district') or '-'}) | severity {d.get('severity')}/5, "
            f"frequency {d.get('frequency')} | suspected causes: "
            f"{', '.join(d.get('suspected_causes') or []) or 'not stated'}")

    user = ("Reports:\n" + "\n".join(lines) +
            f"\n\nDistricts involved: {', '.join(sorted(d for d in districts if d))}"
            f"\nDomains involved: {', '.join(sorted(d for d in domains if d))}"
            f"\nNumber of reports: {len(group)}\n\nAnalyse now.")

    raw = await groq_client.json_call(CONSTELLATION_SYSTEM, user, temperature=0.25)

    if not raw:
        main = max(domains, key=lambda d: sum(
            1 for c in group if c.get("dna", {}).get("primary_domain") == d))
        raw = {
            "is_constellation": len(group) >= 3,
            "root_cause_hypothesis":
                f"Repeated {str(main).replace('_', ' ')} failures across "
                f"{len(districts)} district(s) suggest a shared systemic cause.",
            "reasoning": f"{len(group)} reports from nearby locations share overlapping "
                         "domains and timing, which is unlikely to be coincidence.",
            "confidence": 0.5,
            "mission_name": f"{str(main).replace('_', ' ').title()} Mission",
            "mission_outcome": "Measurably reduce the reported problem across the "
                               "affected cluster within 18 months.",
            "workstreams": [],
            "evidence_gaps": ["Field verification of each reported site."],
        }

    raw["challenge_ids"] = [c.get("challenge_id") for c in group]
    raw["districts"] = sorted(d for d in districts if d)
    raw["domains"] = sorted(d for d in domains if d)
    raw["report_count"] = len(group)
    return raw
