---
title: SAMADHAN GRID
emoji: 💧
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
short_description: Jharkhand Problem-to-Impact Innovation Operating System
---

# SAMADHAN GRID

**Jharkhand Problem-to-Impact Innovation Operating System** — a working prototype.

Not a complaint portal. A system that carries a citizen's spoken problem all the way
to a measured, community-verified improvement in their life — and refuses to call a
project successful until the village says so.

```
Citizen voice (any language, offline-capable)
   ↓  Citizen Understanding Agent
Problem DNA  — 25-field structured record, not a complaint blob
   ↓  Classification · Explainable Priority · Semantic Dedup
Problem Web  — many scattered reports → one root cause → Innovation Mission
   ↓  Human validation gate (AI recommends, an officer decides)
Explainable HEI matching → AI Coalition Composer (university + startup + CSR + NGO + Panchayat)
   ↓  Solution Memory + Failure Intelligence  ("don't rebuild, don't repeat")
Impact Contract signed with the community BEFORE building
   ↓  Evidence-based milestones · Stage-gated funding · TRL / CRL / SRL
Field pilot → Community verdict → Measured impact vs baseline
   ↓
Evidence-to-Impact Ledger · Digital Twin · Policy Insight · Prediction
```

---

## Reaching people with no internet

The citizens this platform exists for are often the least likely to own a smartphone or
have data. So the phone number is on **every page** - in the sidebar, as a banner on the
report screen, and in the site footer - as a tap-to-call link:

> **Helpline 8959 491 068** - call, describe the problem in your own language, and an
> operator fills the form for you.

A helpline call is not a second-class report. The operator files it with
`channel: "helpline"`, which the backend counts as an **assisted submission** - the same
evidence-confidence credit a CSC or Panchayat submission gets, because a trained operator
took it and the caller is traceable. It receives the same reference number, enters the
same officer queue, and is tracked in exactly the same way.

Three ways in, all equal: **call the helpline · walk into a CSC or Panchayat office ·
use this website**.

---

## Stack

| Layer | Technology |
|---|---|
| API | Python **FastAPI** (async), 49 endpoints, OpenAPI docs at `/docs` |
| Database | **MongoDB** (motor async driver) |
| LLM | **Groq** — auto-selects the best chat model your account has (`openai/gpt-oss-120b` here), `whisper-large-v3` for speech-to-text |
| Semantic search | scikit-learn `HashingVectorizer` (word + char n-grams), stateless cosine similarity |
| Frontend | Vanilla JS single-page app + Leaflet map (no build step) |

**Model auto-detection:** Groq rotates its catalogue and accounts differ, so on startup the app asks your
account which models it actually has and picks the best available one. If `GROQ_MODEL` in `.env` is not on
your account it falls through a preference list and logs which model it chose — no silent degradation.

**Graceful degradation:** if `GROQ_API_KEY` is absent or a call fails, every AI service
falls back to a deterministic rule-based path. The platform stays fully usable — it just
gets noticeably smarter with a key (especially cross-language duplicate detection, since
Groq normalises Hindi reports into English Problem DNA).

---

## Run it

**Prerequisites:** Python 3.11+, MongoDB running locally (`mongodb://localhost:27017`).

```bash
pip install -r requirements.txt

# add your free Groq key (https://console.groq.com/keys)
#   edit .env  ->  GROQ_API_KEY=gsk_...

python run.py
```

Open **http://127.0.0.1:8000** · API docs at **/docs**

Click **"Load demo scenario"** in the sidebar. It pushes 8 real citizen reports
(6 of them the Khunti water cluster, in Hindi and English) through the *actual*
pipeline — nothing is canned.

---

## The 8-minute demo walkthrough

| # | Screen | What to show |
|---|---|---|
| 1 | **Report a Problem** | Record a Hindi voice note → Groq Whisper transcribes → Problem DNA appears with domain, vulnerable groups, required expertise. Show the **priority factor bars** — every point is explained. |
| 2 | **Validation Queue** | Officer sees the AI brief and evidence-confidence breakdown, then **overrides** the AI priority. Show the merge action: duplicates are *linked as evidence*, never deleted, and the master's priority recomputes. |
| 3 | **Problem Web** | Run detection. Six separate reports — dry handpumps, failed borewell, lost rabi crop, 3-hour water walks, 4-hour power — collapse into **one groundwater root cause**. Convert it to an Innovation Mission with a measurable outcome. |
| 4 | **Match & Coalition** | BIT Mesra scores 92.3/100 — and the UI shows *why*, factor by factor (5/5 disciplines covered, 3 relevant faculty, 2 labs, 43.9 km from site). Then compose the full coalition: 2 universities + IoT startup + sensor MSME + CSR + NGO + Panchayat + department, each with a defined job. |
| 5 | **Project Workspace** | Try to advance to *prototype* → **blocked**: "Run the Solution Memory review first." Run it → it surfaces a **real past failure**: solar water ATMs abandoned because ₹38,000/yr maintenance exceeded what Panchayats could pay. Team adapts instead of rebuilding. |
| 6 | Same screen | Sign the **Impact Contract** (metrics agreed before building). Try a milestone with no file → **422, evidence is mandatory**. Set TRL 7 / CRL 3 → system warns *"technically ahead of the community — the classic pattern behind demos nobody uses."* |
| 7 | Same screen | Village records its verdict. Record endline: water walk 3000 m → 200 m. **100% of metrics improved, ₹404.93 per person.** |
| 8 | **Command Dashboard** | State Innovation Map, systemic insight, seasonal prediction, and the **Digital Twin**: *is the problem itself shrinking, across every project and every rupee?* |

---

## What makes it an OS, not a portal

1. **Problem DNA** — standardised, machine-reasonable representation of every report
2. **Explainable everything** — no bare "high/medium/low"; every score decomposes into weighted factors with reasons
3. **Problem Web** — semantic + geographic + temporal + domain-relationship clustering finds shared root causes
4. **Innovation Missions** — fund an *outcome*, not thirty disconnected projects
5. **Coalition Composer** — the whole ecosystem, each member with a defined job
6. **Solution Memory + Failure Intelligence** — failures are kept and proactively surfaced
7. **Impact Contract** — success defined with the community *before* work starts
8. **Three readiness axes** — TRL ≠ Community Readiness ≠ Scale Readiness
9. **Stage-gated funding** — money follows evidence; blocked without an Impact Contract
10. **Evidence-based milestones** — no proof, no completion (enforced, returns 422)
11. **Evidence-to-Impact Ledger** — append-only, attributable, timestamped
12. **Digital Twin** — flags *"8 projects, ₹X spent, 12% improvement — reconsider strategy"*
13. **Innovation Passport** — student's verified real-impact record, backed by ledger entries

Human oversight is enforced in code: challenge rejection, prioritisation, allocation,
funding approval and milestone approval all require a named human actor.

---

## Layout

```
app/
  config.py            domains, districts, lifecycle states, languages, roles
  db.py                MongoDB + the append-only Evidence-to-Impact Ledger
  seed.py              7 HEI capability profiles, 10 partners, 13 knowledge items, 8 demo reports
  ai/
    groq_client.py     resilient Groq wrapper (JSON mode, Whisper, never crashes a request)
    understanding.py   Citizen Understanding Agent  -> Problem DNA
    priority.py        Explainable priority (8 weighted factors) + Evidence Confidence
    similarity.py      Duplicate detection + Problem Constellation clustering
    matching.py        HEI matching (6 explainable factors) + consortium gap analysis
    coalition.py       AI Coalition Composer
    memory.py          Solution Memory + Failure Intelligence
    impact.py          Impact Contract, TRL/CRL/SRL, measurement, Digital Twin
    insight.py         Policy insight, seasonal prediction, project risk
  routers/
    challenges.py      submission, voice, evidence, corroboration, community feedback
    governance.py      review workflow, constellations, missions, matching, allocation
    projects.py        lifecycle gates, milestones, funding, readiness, impact
    analytics.py       dashboard, map, insights, digital twin, registry, passport
static/                single-page UI (index.html, app.js, style.css)
```

---

## Honesty notes

- Institution **names** are real Jharkhand institutions, but all capability profiles,
  laboratories, past projects and partner organisations are **synthetic demo data**.
  **Faculty names are placeholders and do not refer to real people.** In production
  institutions would maintain and verify their own profiles.
- The pilot numbers in the walkthrough are illustrative demo readings, not real results.
- Predictive output is decision support based on reporting patterns — not a forecast.
