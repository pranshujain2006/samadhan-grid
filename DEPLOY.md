# Hosting SAMADHAN GRID for free

## What this project actually needs

Two facts decide the answer, and they are specific to this project:

| Requirement | Why it matters |
|---|---|
| **265 MB of dependencies** (scipy 118 MB + sklearn 42 MB + numpy 42 MB + the rest) | Kills every serverless free tier |
| **MongoDB** | Needs a hosted database, not a file |
| **Writes uploaded evidence to disk** | Free tiers have an ephemeral disk |
| **Long AI requests** (Groq calls take 5-20 s) | Rules out hosts with a short request timeout |

Because of the 265 MB, **Vercel and Netlify cannot host this** — their serverless
functions cap at 250 MB unzipped. You need a **container host**.

---

## Recommendation

### 🥇 Hugging Face Spaces (Docker) + MongoDB Atlas

**Why it wins for this project:** no credit card, free forever, generous RAM, and it
does not care that your dependencies are 265 MB. The public URL is easy to hand to a
judge.

| | |
|---|---|
| Cost | Free |
| Credit card | **Not required** |
| RAM / CPU | 16 GB / 2 vCPU on the free CPU tier |
| Sleeps? | Only after ~48 h with no visitors, and wakes quickly |
| Big dependencies | Fine — it is a real container |
| Secrets | Built-in, for `GROQ_API_KEY` |
| Catch | The Space is public by default, so your code is visible. For a hackathon that is usually a plus. |

### 🥈 Render (free web service) + MongoDB Atlas

Cleaner developer experience and a nicer URL, but the free tier **spins down after 15
minutes of inactivity** and takes roughly 50 seconds to wake. If a judge opens your link
cold, they stare at a blank page for almost a minute. That is the only reason it is
second.

### 🥉 Oracle Cloud Always Free

A genuinely free, always-on VM (4 ARM cores, 24 GB RAM). Best performance of the three
and it never sleeps — but it needs a credit card for identity verification and you set
up the server yourself. Worth it if this becomes a real deployment rather than a demo.

### Database, whichever host you pick: **MongoDB Atlas M0**

Free forever, 512 MB, no credit card, and it does not sleep. There is no reason to use
anything else here.

---

## Deploy to Hugging Face Spaces

### 1. Create the database (5 minutes)

1. Sign up at <https://www.mongodb.com/cloud/atlas/register>
2. Create a free **M0** cluster.
3. **Database Access** → add a user, note the password.
4. **Network Access** → Add IP Address → **Allow access from anywhere** (`0.0.0.0/0`).
   Free hosts do not give you a fixed IP, so this is necessary.
5. **Connect** → *Drivers* → copy the connection string. It looks like:
   `mongodb+srv://USER:PASSWORD@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority`

### 2. Create the Space

1. <https://huggingface.co/new-space> → name it, choose **Docker** → *Blank*, keep it Public.
2. Push this project to it:

```bash
git init
git add .
git commit -m "SAMADHAN GRID"
git remote add space https://huggingface.co/spaces/<your-username>/<space-name>
git push space main
```

`.dockerignore` already excludes `.env`, `uploads/`, screenshots and the PPT files, so
your Groq key is never pushed.

### 3. Set the secrets

In the Space → **Settings** → **Variables and secrets**, add:

| Name | Type | Value |
|---|---|---|
| `GROQ_API_KEY` | Secret | your Groq key |
| `MONGODB_URI` | Secret | the Atlas connection string from step 1 |
| `GROQ_MODEL` | Variable | `openai/gpt-oss-120b` |
| `EPHEMERAL_DISK` | Variable | `true` |

`HOST`, `PORT` and `UPLOAD_DIR` are already set correctly in the `Dockerfile`.

### 4. Load the demo data

Once it builds, open your Space URL and click **"Load demo"** in the sidebar, then walk
steps 2-6 once so the dashboard has real numbers.

---

## Deploy to Render instead

1. Push this project to GitHub.
2. <https://render.com> → **New** → **Web Service** → connect the repo.
3. Render detects the `Dockerfile` automatically. Choose the **Free** instance.
4. Add the same four environment variables as above.
5. Render injects its own `PORT`; the `Dockerfile` already reads it.

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
