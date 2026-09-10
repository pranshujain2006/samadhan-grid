"""Citizen Understanding Agent.

Converts informal citizen language (any language, spoken or typed) into the
structured "Problem DNA" that the rest of the platform reasons over.
"""
from __future__ import annotations

import re
from typing import Any

from ..config import DOMAINS
from . import groq_client

SYSTEM = """You are the Citizen Understanding Agent of SAMADHAN GRID, the societal
innovation platform of the Government of Jharkhand, India.

A citizen has described a real problem in their own words. They may write in Hindi,
English, Hinglish, or a tribal language (Santhali, Ho, Mundari, Kurukh). They are not
trained in government language and should not have to be.

Your job: convert their words into a rigorous, structured "Problem DNA" record.

Rules:
- NEVER invent facts the citizen did not imply. If something is unknown, use null or
  an empty list. Do not hallucinate numbers of people or causes.
- Estimates you DO make must be conservative and clearly derivable from the text
  (e.g. "the whole village" for a village-level water problem).
- Write `title` and `description` in clear simple English. Keep `summary_local` in the
  citizen's own language so they can confirm you understood them.
- `primary_domain` MUST be exactly one value from the allowed domain list.
- `secondary_domains` captures the real fact that societal problems are multi-domain.
  A drinking water shortage is also women's welfare, public health and agriculture.
- `required_expertise` should name the academic/technical disciplines needed to solve
  it, because this drives university matching later.
- Return ONLY a JSON object.

Allowed domains: {domains}

Return exactly this JSON shape:
{{
  "title": "short specific title, max 90 chars",
  "description": "2-4 sentence neutral restatement in simple English",
  "summary_local": "1-2 sentence summary in the citizen's own language",
  "detected_language": "ISO code like hi, en, sat, ho, mun, kru",
  "primary_domain": "one allowed domain",
  "secondary_domains": ["other allowed domains"],
  "subdomain": "specific sub-area e.g. drinking water supply",
  "affected_community": "who is affected, in words",
  "people_affected_estimate": integer or null,
  "urgency": 1-5,
  "severity": 1-5,
  "frequency": "one_time | seasonal | recurring | continuous | unknown",
  "duration": "how long it has been happening, or unknown",
  "vulnerable_groups": ["women","children","elderly","tribal_households","persons_with_disability","farmers","daily_wage_workers"],
  "suspected_causes": ["short cause phrases"],
  "existing_infrastructure": "what already exists there, or unknown",
  "previous_attempts": "what was tried before, or unknown",
  "expected_outcome": "what good would look like for this community",
  "govt_departments": ["likely responsible departments in Jharkhand"],
  "possible_interventions": ["technical or process interventions worth exploring"],
  "required_expertise": ["academic disciplines needed"],
  "keywords": ["6-10 search keywords in English"],
  "is_emergency": true or false,
  "confidence": 0.0-1.0
}}"""

# --------------------------------------------------------------------- fallback

_KEYWORDS: dict[str, list[str]] = {
    "water_resources": ["water", "handpump", "hand pump", "borewell", "well", "tap",
                        "pani", "जल", "पानी", "नल", "चापाकल", "groundwater", "tubewell",
                        "drinking water", "tanker", "pond", "river", "supply"],
    "sanitation": ["toilet", "latrine", "sewage", "drain", "shauchalay", "शौचालय",
                   "नाली", "open defecation", "septic"],
    "waste_management": ["garbage", "waste", "dump", "kachra", "कचरा", "litter",
                         "plastic", "landfill", "trash"],
    "healthcare": ["hospital", "doctor", "clinic", "medicine", "health", "asha",
                   "swasthya", "स्वास्थ्य", "अस्पताल", "दवा", "phc", "chc", "illness",
                   "disease", "malaria", "ambulance", "vaccination"],
    "education": ["school", "teacher", "student", "class", "vidyalaya", "शिक्षा",
                  "स्कूल", "शिक्षक", "study", "dropout", "anganwadi", "book"],
    "agriculture": ["crop", "farm", "farmer", "irrigation", "kisan", "खेत", "फसल",
                    "किसान", "सिंचाई", "seed", "fertilizer", "pest", "harvest", "soil"],
    "environment": ["forest", "tree", "pollution", "air", "jungle", "प्रदूषण", "जंगल",
                    "deforestation", "mining dust", "contamination"],
    "energy": ["electricity", "power", "solar", "bijli", "बिजली", "light", "outage",
               "transformer", "grid"],
    "transportation": ["road", "bus", "transport", "bridge", "sadak", "सड़क", "पुल",
                       "vehicle", "connectivity", "commute"],
    "employment": ["job", "employment", "work", "rozgar", "रोजगार", "wage", "mgnrega",
                   "unemployment", "livelihood"],
    "women_child_welfare": ["women", "girl", "child", "mahila", "महिला", "बच्चे",
                            "anganwadi", "maternal", "pregnant", "nutrition"],
    "urban_development": ["ward", "municipal", "street light", "footpath", "drainage",
                          "housing", "slum"],
    "rural_livelihood": ["shg", "self help group", "livelihood", "dairy", "poultry",
                         "forest produce", "tendu", "lac", "handicraft"],
    "accessibility": ["disabled", "divyang", "दिव्यांग", "wheelchair", "ramp",
                      "accessibility"],
    "disaster_resilience": ["flood", "drought", "landslide", "baadh", "बाढ़", "सूखा",
                            "cyclone", "earthquake", "disaster"],
    "digital_governance": ["online", "portal", "certificate", "aadhaar", "internet",
                           "network", "digital", "form"],
    "public_administration": ["office", "officer", "corruption", "delay", "application",
                              "pension", "ration", "scheme"],
    "social_inclusion": ["caste", "tribal", "adivasi", "आदिवासी", "discrimination",
                         "minority", "exclusion"],
}

_VULNERABLE = {
    "women": ["women", "woman", "mahila", "महिला", "girl", "girls"],
    "children": ["child", "children", "बच्चे", "kids", "student", "school"],
    "elderly": ["elderly", "old", "बुजुर्ग", "senior"],
    "tribal_households": ["tribal", "adivasi", "आदिवासी", "santhal", "munda", "oraon"],
    "farmers": ["farmer", "kisan", "किसान", "crop", "farm"],
    "persons_with_disability": ["disabled", "divyang", "दिव्यांग", "handicap"],
    "daily_wage_workers": ["labour", "labor", "mazdoor", "मजदूर", "daily wage"],
}

_URGENT = ["urgent", "emergency", "dying", "died", "death", "outbreak", "collapse",
           "immediately", "तुरंत", "मौत", "गंभीर", "critical", "danger"]

_EXPERTISE = {
    "water_resources": ["Civil Engineering", "Hydrology", "Environmental Engineering",
                        "IoT & Sensors", "Data Science"],
    "sanitation": ["Civil Engineering", "Public Health", "Behavioural Science"],
    "waste_management": ["Environmental Engineering", "Mechanical Engineering",
                         "Operations Research"],
    "healthcare": ["Public Health", "Biomedical Engineering", "Data Science",
                   "Community Medicine"],
    "education": ["Education Technology", "Pedagogy", "Computer Science", "Psychology"],
    "agriculture": ["Agricultural Engineering", "Soil Science", "Agronomy",
                    "Remote Sensing", "Data Science"],
    "environment": ["Environmental Science", "Remote Sensing", "Ecology"],
    "energy": ["Electrical Engineering", "Renewable Energy", "Power Systems"],
    "transportation": ["Civil Engineering", "Transportation Planning", "GIS"],
    "employment": ["Economics", "Skill Development", "Data Science"],
    "women_child_welfare": ["Social Work", "Public Health", "Nutrition Science"],
    "urban_development": ["Urban Planning", "Civil Engineering", "GIS"],
    "rural_livelihood": ["Rural Management", "Economics", "Agribusiness"],
    "accessibility": ["Assistive Technology", "Design", "Rehabilitation Science"],
    "disaster_resilience": ["Disaster Management", "Remote Sensing", "Civil Engineering"],
    "digital_governance": ["Computer Science", "Human Computer Interaction"],
    "public_administration": ["Public Policy", "Operations Research"],
    "social_inclusion": ["Sociology", "Public Policy", "Social Work"],
}

_DEPARTMENTS = {
    "water_resources": ["Drinking Water & Sanitation Department", "Water Resources Department"],
    "sanitation": ["Drinking Water & Sanitation Department", "Urban Development Department"],
    "waste_management": ["Urban Development & Housing Department"],
    "healthcare": ["Health, Medical Education & Family Welfare Department"],
    "education": ["School Education & Literacy Department"],
    "agriculture": ["Agriculture, Animal Husbandry & Co-operative Department"],
    "environment": ["Forest, Environment & Climate Change Department"],
    "energy": ["Energy Department", "JBVNL"],
    "transportation": ["Road Construction Department", "Transport Department"],
    "employment": ["Labour, Employment & Training Department"],
    "women_child_welfare": ["Women, Child Development & Social Security Department"],
    "urban_development": ["Urban Development & Housing Department"],
    "rural_livelihood": ["Rural Development Department", "JSLPS"],
    "accessibility": ["Women, Child Development & Social Security Department"],
    "disaster_resilience": ["Disaster Management Department"],
    "digital_governance": ["Information Technology & e-Governance Department"],
    "public_administration": ["Personnel & Administrative Reforms Department"],
    "social_inclusion": ["Welfare Department"],
}


def _score_domains(text: str) -> list[tuple[str, int]]:
    low = text.lower()
    scored = []
    for dom, words in _KEYWORDS.items():
        hits = sum(1 for w in words if w in low)
        if hits:
            scored.append((dom, hits))
    scored.sort(key=lambda x: -x[1])
    return scored


def _fallback_dna(text: str, language: str) -> dict[str, Any]:
    """Deterministic extraction used when Groq is unavailable."""
    low = text.lower()
    scored = _score_domains(text)
    primary = scored[0][0] if scored else "public_administration"
    secondary = [d for d, _ in scored[1:4]]

    vulnerable = [g for g, words in _VULNERABLE.items() if any(w in low for w in words)]
    urgent_hit = any(w in low for w in _URGENT)

    # crude population estimate from any number mentioned near household/people words
    people = None
    m = re.search(r"(\d{2,6})\s*(households?|people|families|villagers|घर|लोग|परिवार)", low)
    if m:
        people = int(m.group(1))

    seasonal = any(w in low for w in ["summer", "winter", "monsoon", "rainy", "गर्मी",
                                      "बरसात", "every year", "har saal", "seasonal"])
    title = re.sub(r"\s+", " ", text.strip())[:88]

    return {
        "title": title or "Citizen reported issue",
        "description": text.strip()[:600],
        "summary_local": text.strip()[:220],
        "detected_language": language or "en",
        "primary_domain": primary,
        "secondary_domains": secondary,
        "subdomain": primary.replace("_", " "),
        "affected_community": "Local community at the reported location",
        "people_affected_estimate": people,
        "urgency": 5 if urgent_hit else (4 if seasonal else 3),
        "severity": 4 if urgent_hit else 3,
        "frequency": "seasonal" if seasonal else "recurring",
        "duration": "unknown",
        "vulnerable_groups": vulnerable,
        "suspected_causes": [],
        "existing_infrastructure": "unknown",
        "previous_attempts": "unknown",
        "expected_outcome": "The reported problem is resolved for the affected community",
        "govt_departments": _DEPARTMENTS.get(primary, []),
        "possible_interventions": [],
        "required_expertise": _EXPERTISE.get(primary, ["Engineering", "Data Science"]),
        "keywords": [w for w in re.findall(r"[a-zA-Z]{4,}", low)][:10],
        "is_emergency": urgent_hit,
        "confidence": 0.45,
        "ai_source": "fallback",
    }


def _coerce(raw: dict[str, Any], text: str, language: str) -> dict[str, Any]:
    """Validate and repair whatever the LLM returned."""
    base = _fallback_dna(text, language)
    out = dict(base)

    def s(key, default=None):
        v = raw.get(key)
        return v if isinstance(v, str) and v.strip() else default

    def lst(key):
        v = raw.get(key)
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()][:8]
        return None

    def num(key, lo, hi, default):
        v = raw.get(key)
        try:
            v = int(v)
            return max(lo, min(hi, v))
        except (TypeError, ValueError):
            return default

    out["title"] = (s("title") or base["title"])[:120]
    out["description"] = s("description") or base["description"]
    out["summary_local"] = s("summary_local") or base["summary_local"]
    out["detected_language"] = s("detected_language") or language or "en"
    out["subdomain"] = s("subdomain") or base["subdomain"]
    out["affected_community"] = s("affected_community") or base["affected_community"]
    out["existing_infrastructure"] = s("existing_infrastructure") or "unknown"
    out["previous_attempts"] = s("previous_attempts") or "unknown"
    out["expected_outcome"] = s("expected_outcome") or base["expected_outcome"]
    out["frequency"] = s("frequency") or base["frequency"]
    out["duration"] = s("duration") or "unknown"

    pd = raw.get("primary_domain")
    out["primary_domain"] = pd if pd in DOMAINS else base["primary_domain"]
    sd = lst("secondary_domains") or []
    out["secondary_domains"] = [d for d in sd if d in DOMAINS and d != out["primary_domain"]]

    for key in ("vulnerable_groups", "suspected_causes", "possible_interventions",
                "required_expertise", "keywords", "govt_departments"):
        v = lst(key)
        if v:
            out[key] = v

    out["urgency"] = num("urgency", 1, 5, base["urgency"])
    out["severity"] = num("severity", 1, 5, base["severity"])

    ppl = raw.get("people_affected_estimate")
    try:
        out["people_affected_estimate"] = int(ppl) if ppl is not None else base["people_affected_estimate"]
    except (TypeError, ValueError):
        pass

    out["is_emergency"] = bool(raw.get("is_emergency", base["is_emergency"]))
    try:
        out["confidence"] = max(0.0, min(1.0, float(raw.get("confidence", 0.8))))
    except (TypeError, ValueError):
        out["confidence"] = 0.8
    out["ai_source"] = "groq"
    return out


async def build_problem_dna(text: str, *, language: str = "auto",
                            location: dict[str, Any] | None = None,
                            evidence: list[dict[str, Any]] | None = None
                            ) -> dict[str, Any]:
    """Main entry point: informal citizen text -> structured Problem DNA."""
    loc = location or {}
    ev = evidence or []
    loc_line = ", ".join(str(loc.get(k)) for k in
                         ("village_or_ward", "panchayat_or_ulb", "block", "district")
                         if loc.get(k))
    ev_line = ", ".join(sorted({e.get("kind", "file") for e in ev})) or "none"

    user = (
        f"Citizen report (verbatim):\n\"\"\"\n{text.strip()}\n\"\"\"\n\n"
        f"Reported location: {loc_line or 'not specified'}, Jharkhand\n"
        f"GPS provided: {'yes' if loc.get('lat') else 'no'}\n"
        f"Evidence attached: {ev_line}\n"
        f"Declared language: {language}\n\n"
        "Produce the Problem DNA JSON now."
    )

    raw = await groq_client.json_call(
        SYSTEM.format(domains=", ".join(DOMAINS)), user, temperature=0.15)

    if not raw:
        dna = _fallback_dna(text, language if language != "auto" else "en")
    else:
        dna = _coerce(raw, text, language if language != "auto" else "en")

    dna["original_text"] = text.strip()
    dna["evidence_available"] = sorted({e.get("kind", "file") for e in ev})
    return dna
