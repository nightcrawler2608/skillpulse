# Putting SkillPulse online (Hugging Face Spaces, free)

The app runs as a **Docker Space** on Hugging Face's free CPU tier (2 vCPU, 16 GB RAM).
It sleeps after 48 hours without visitors and wakes up (about 1–2 minutes) on the next visit.

## One-time setup

### 1. A limited database user for the website
The website only needs to read jobs and add anonymous feedback, so it gets its own user that
can't change or delete data:

```powershell
python -m skillpulse.db.app_role
```

This creates role `skillpulse_app` and saves its connection string as `APP_DATABASE_URL` in
your `.env` (the password is never printed). Running it again makes a new password.

### 2. Create the Space (huggingface.co)
1. Sign in → your profile picture → **New Space**.
2. Name: `skillpulse` · License: your choice · **SDK: Docker → Blank** · Hardware: **CPU basic (free)** ·
   Visibility: **Public**.
3. In the new Space: **Settings → Variables and secrets → New secret**, add:
   - `DATABASE_URL` = the value of `APP_DATABASE_URL` from your `.env` (not the owner one)
   - `GEMINI_API_KEY` = your Gemini key

### 3. Let GitHub deploy it
1. Hugging Face → Settings → **Access Tokens** → New token, type **Write** (or fine-grained
   with write access to this Space only). Copy it.
2. GitHub repo → Settings → Secrets and variables → Actions:
   - **Secrets** tab → New secret `HF_TOKEN` = that token
   - **Variables** tab → New variable `HF_SPACE` = `<your-hf-username>/skillpulse`
3. Actions tab → **Deploy to Hugging Face** → Run workflow. After that, every push that changes
   the app deploys automatically.

The first build takes ~5–10 minutes (it installs PyTorch and downloads the language model).
Watch it in the Space's **Logs** tab.

## What gets uploaded
Only `Dockerfile`, `pyproject.toml`, `src/`, `app/` (without the labelling tool),
`data/skills/` and `.streamlit/` (see `scripts/deploy_space.py`). Never `.env`, job data
files, evaluation data or resumes. Secrets live only in the Space settings.

## Switches
| Variable | Effect |
|---|---|
| `SKILLPULSE_LLM=off` | Learning plans use the template only (no Gemini calls) |
| `GEMINI_MODEL` | Try a specific Gemini model first |
| `SKILLPULSE_TRACKING=off` | Don't record anonymous usage/feedback (used for local testing) |
