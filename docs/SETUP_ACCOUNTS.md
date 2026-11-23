# Phase 0 — Free account setup (step by step)

You need 5 free accounts. None of them need a credit card. Total time: ~30–40 minutes.

**Golden rule:** keys go **only** into your local `.env` file. Never paste them into chat,
screenshots, WhatsApp, or GitHub.

First, create your `.env` file (in PowerShell, inside the project folder):

```powershell
copy .env.example .env
notepad .env
```

Website screens change over time. If a button has a slightly different name, look for the closest match.

---

## 1. GitHub — code hosting + free daily automation
1. Go to https://github.com and sign up (use your college or personal email).
2. Nothing to put in `.env`. We'll create the repository together later.
3. Tip: apply for the **GitHub Student Developer Pack** (free, uses your college email/ID).
   It isn't required, but it looks good and gives extra free tools.

## 2. Adzuna — job data API
1. Go to https://developer.adzuna.com and click **Register**.
2. Fill in the form. For website/app description you can write:
   "Final-year student project analysing job-market skill demand in India."
3. After logging in, open the **Dashboard / API Access Details** page.
4. Copy **Application ID** → `ADZUNA_APP_ID=` in `.env`
5. Copy **Application Key** → `ADZUNA_APP_KEY=` in `.env`

## 3. Neon — free PostgreSQL database
1. Go to https://neon.tech and sign up (signing in with GitHub is easiest).
2. Create a project:
   - Name: `skillpulse`
   - Postgres version: the default (latest)
   - Region: choose the one closest to India (e.g. **AWS Asia Pacific – Singapore**)
3. On the project dashboard click **Connect**. Copy the **connection string**. It looks like
   `postgresql://user:password@ep-xxxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require`
4. Paste it → `DATABASE_URL=` in `.env` (the whole thing, on one line).

## 4. Google AI Studio — Gemini LLM (free tier)
1. Go to https://aistudio.google.com and sign in with a Google account.
2. Click **Get API key** → **Create API key**.
3. Copy it → `GEMINI_API_KEY=` in `.env`

## 5. Hugging Face — free app hosting (needed in Phase 6, but set it up now)
1. Go to https://huggingface.co/join and sign up.
2. Open **Settings → Access Tokens → Create new token**.
   - Type: **Write**
   - Name: `skillpulse-deploy`
3. Copy it → `HF_TOKEN=` in `.env`

---

## Check everything works

```powershell
.\.venv\Scripts\Activate.ps1
python scripts/check_setup.py
```

You want to see `[OK]` on all four lines. If a line says `FAIL`, the message tells you why
(usually a copy-paste mistake in `.env`: an extra space, or a missing part of the key).
