# Putting SkillPulse online (Streamlit Community Cloud, free)

**Why not Hugging Face?** In November 2026 Hugging Face started requiring a paid PRO plan for
Docker and Gradio Spaces on its free CPU ("Static Spaces are free for everyone, but hosting
Gradio and Docker Spaces on free cpu-basic requires a PRO subscription"). The `Dockerfile` and
`scripts/deploy_space.py` still work for any Docker host, but the free route is now
Streamlit Community Cloud.

**Streamlit Community Cloud (free):** deploys straight from this GitHub repo; up to ~2.7 GB
memory (the app uses ~740 MB); sleeps after 12 hours without visitors and wakes on the next
visit (about a minute). Apps are hosted in the US.

## One-time setup

### 1. A limited database user for the website (done once)
```powershell
python -m skillpulse.db.app_role
```
Creates role `skillpulse_app` (read everything; add only anonymous feedback/usage rows) and
saves its connection string as `APP_DATABASE_URL` in your `.env`. The password is never printed.

### 2. Deploy (share.streamlit.io)
1. Go to **share.streamlit.io** → sign in with **GitHub** → allow access to your repositories.
2. **Create app** → *Deploy a public app from GitHub*:
   - Repository: `nightcrawler2608/skillpulse` · Branch: `main`
   - Main file path: `app/main.py`
   - App URL: pick a name, e.g. `skillpulse`
3. **Advanced settings**:
   - Python version: any of **3.11–3.14** (requirements list a CPU PyTorch file for each)
   - Secrets: paste these two lines with your values from `.env`:
     ```toml
     DATABASE_URL = "the value of APP_DATABASE_URL (the limited user, NOT the owner one)"
     GEMINI_API_KEY = "your Gemini key"
     ```
4. **Deploy**. The first build takes ~5 minutes (it installs CPU PyTorch). After that, every
   push to `main` updates the site automatically.

## What the host uses
- `app/requirements.txt`: the web app's dependencies (CPU-only PyTorch as direct files, one per
  Python version, because the host installs with `uv`, which won't mix package indexes).
- `.streamlit/config.toml`: theme, upload limit, telemetry off, developer toolbar hidden.
- Secrets from the Secrets box are copied into environment variables by `app/main.py`.
- Never uploaded anywhere: `.env`, job data files, evaluation data, resumes.

## Switches
| Variable | Effect |
|---|---|
| `SKILLPULSE_LLM=off` | Learning plans use the template only (no Gemini calls) |
| `GEMINI_MODEL` | Try a specific Gemini model first |
| `SKILLPULSE_TRACKING=off` | Don't record anonymous usage/feedback (used for local testing) |

## Tested before going live
A clean Linux container with Python 3.12, `uv` and only `app/requirements.txt`, no `.env`,
secrets only from `.streamlit/secrets.toml` (limited DB user): home, resume analysis, job
matches and a Gemini-worded plan all worked; memory ~740 MB.
