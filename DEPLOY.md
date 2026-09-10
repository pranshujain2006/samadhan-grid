# Hosting SAMADHAN GRID for free

> **Checked September 2026.** Free tiers change often - Hugging Face moved Docker Spaces
> behind a PRO subscription, and Render now asks for a card. Verify before you commit.

## What this project needs

| Requirement | Status |
|---|---|
| Dependencies | **~110 MB** (numpy + FastAPI stack). scikit-learn and scipy were removed - see below |
| Docker image | **368 MB** |
| Memory at runtime | **66 MB peak**, measured under a 512 MB cap |
| Database | MongoDB (Atlas M0 free) |
| Uploaded evidence | Written to disk - wiped on restart on any free tier |

### Why it is this small

The semantic duplicate detection originally used `scikit-learn`'s `HashingVectorizer`
with `scipy` sparse matrices - together about 160 MB. That is replaced by a ~30-line
pure-numpy hashing vectoriser in `app/ai/similarity.py` that does the same job: hash word
and character n-grams into a fixed 4096-wide vector, L2-normalise, compare with cosine.

Measured on the same data, duplicate detection came out slightly **better** after the
change, not worse. It also removed the need for `scipy` entirely.

---

## Platform comparison (September 2026)

| Platform | Free | Card needed | Sleeps | Verdict |
|---|---|---|---|---|
| **Koyeb Hobby** | Yes | Usually no | Scale-to-zero | **Best free option now** - 512 MB is plenty, we use 66 MB |
| Render free | Yes | **Yes** (verification) | after 15 min (~50 s wake) | Reliable, but the card and the cold start hurt |
| Google Cloud Run | Generous free tier | Yes | Scale-to-zero | Excellent if you will add a card |
| Oracle Always Free | Yes | Yes | Never | Best machine, most setup |
| Fly.io | Small allowance | Yes | Configurable | No longer clearly free |
| Hugging Face Spaces | **Docker needs PRO** | - | - | **No longer free for this** |
| Vercel / Netlify | Yes | No | - | Serverless only - cannot run this |

Database on all of them: **MongoDB Atlas M0**, free forever, no card.

---

## Deploy to Koyeb

### 1. MongoDB Atlas first (5 minutes)

1. <https://www.mongodb.com/cloud/atlas/register> - free, no card
2. Create a free **M0** cluster
3. **Database Access** - add a user, save the password
4. **Network Access** - allow `0.0.0.0/0` (free hosts have no fixed IP)
5. **Connect - Drivers** - copy the `mongodb+srv://...` string

### 2. Push the code to GitHub

```bash
git remote add origin https://github.com/<you>/samadhan-grid.git
git push -u origin main
```

`.gitignore` already excludes `.env`, so your Groq key is never pushed.

### 3. Create the Koyeb service

1. <https://app.koyeb.com> - sign up with GitHub
2. **Create Service** - **GitHub** - pick the repo
3. Koyeb detects the `Dockerfile` automatically
4. Instance type: **Free**
5. Port: **7860**
6. Environment variables:

| Name | Type | Value |
|---|---|---|
| `GROQ_API_KEY` | Secret | your Groq key |
| `MONGODB_URI` | Secret | the Atlas string from step 1 |
| `GROQ_MODEL` | Plain | `openai/gpt-oss-120b` |
| `EPHEMERAL_DISK` | Plain | `true` |

7. Deploy. First build takes a few minutes.

### 4. Load the demo

Open the URL, click **Load demo** in the sidebar, then walk steps 2-6 once so the
dashboard has real numbers.

---

## The one honest limitation

Every free tier gives you an **ephemeral disk**. Photos, videos and voice notes uploaded
as evidence live in `uploads/` and **will be deleted on every restart or redeploy**. The
database records survive; the files behind them do not.

That is acceptable for a demo, and setting `EPHEMERAL_DISK=true` makes the server log say
so plainly at startup instead of letting you discover it later.

For a real deployment, store evidence in object storage instead. Two good free options:

- **MongoDB GridFS** — you already have Atlas, and it keeps everything in one place
  (counts against the 512 MB).
- **Cloudinary** free tier — better if the evidence is mostly photos and video.

---

## Quick comparison

| Platform | Free forever | Card needed | Handles 265 MB | Sleeps | Verdict |
|---|---|---|---|---|---|
| **HF Spaces (Docker)** | Yes | No | Yes | after ~48 h | **Best for this project** |
| Render free | Yes | No | Yes | after 15 min (~50 s wake) | Good, but the cold start hurts a live demo |
| Oracle Always Free | Yes | Yes | Yes | Never | Best performance, most setup |
| Koyeb free | Yes | No | Yes | No | Reasonable alternative |
| Fly.io | Limited allowance | Yes | Yes | Configurable | Fine, but no longer clearly free |
| Railway | Trial credit only | Yes | Yes | No | Not free any more |
| **Vercel / Netlify** | Yes | No | **No — 250 MB cap** | n/a | **Cannot host this project** |
| PythonAnywhere free | Yes | No | Tight | No | Awkward for ASGI/FastAPI |

Free tiers change often — check the current limits before you commit to one.
