# Job Alert Agent

A small serverless agent that searches a public job-board API daily for
chosen keywords and emails new matches — built entirely on free infrastructure
(GitHub Actions + a public government API + a transactional email API).

No server to maintain, no paid subscription, no database. It runs on a
schedule in the cloud and simply stops existing between runs.

## Why I built this

I wanted a practical, end-to-end example of a lightweight automation agent —
something that fetches live external data, applies simple decision logic, and
takes an action (sending an email) completely unattended, on a recurring
schedule, without any infrastructure to manage or pay for. It also solves a
real problem for my own job search: instead of manually re-checking a job
board, I get only what's new, every morning.

## How it works

```
GitHub Actions (cron, daily)
        │
        ▼
 job_alert.py
        │
        ├─▶ Arbetsförmedlingen JobSearch API   (free, public, no key)
        │        — search by keyword, get structured JSON back
        │
        ├─▶ filter: keep only postings published since the last run
        │
        └─▶ Resend API   (free tier)
                 — email the results, or "no new matches today"
```

Each run is stateless — rather than tracking what's already been sent (which
would need a database), the script simply filters by publication timestamp,
keeping only postings newer than a configurable lookback window. Simple,
no moving parts to break.

## Tech stack

- **Python 3.12** — `requests` for HTTP, standard library for everything else
- **GitHub Actions** — free scheduled compute (cron), secrets management
- **[Arbetsförmedlingen JobSearch API](https://jobtechdev.se/en/components/jobsearch)** —
  Sweden's official public employment service job-ad API, CC0-licensed, no
  authentication required
- **[Resend](https://resend.com)** — transactional email API (chosen over raw
  SMTP because cloud CI providers like GitHub Actions are frequently blocked
  by Gmail's SMTP servers as a spam-prevention measure; an HTTP API sidesteps
  that entirely)

## Setup

1. **Fork or clone this repo.**

2. **Get a free Resend API key** at [resend.com](https://resend.com) →
   API Keys → Create API Key. No domain verification needed to send to your
   own signup email.

3. **Add repository secrets** (Settings → Secrets and variables → Actions →
   New repository secret). See `.env.example` for the full list — in short:

   | Secret | Purpose |
   |---|---|
   | `SEARCH_KEYWORDS` | Comma-separated search terms |
   | `MUNICIPALITIES` | Optional location filter (blank = nationwide) |
   | `LOOKBACK_HOURS` | Time window for "new" postings |
   | `RESEND_API_KEY` | From step 2 |
   | `TO_EMAIL` | Where to send alerts |

4. **Set your schedule** by editing the cron line in
   `.github/workflows/job-alert.yml` (GitHub Actions cron always runs in UTC).

5. **Test it**: Actions tab → "Job Alert" → "Run workflow". The log prints
   what it found before emailing, so you can verify without checking your inbox.

## AI relevance scoring (optional)

By default this does plain keyword matching. Setting these three additional
secrets turns on an AI scoring step: each job's description is sent to
Gemini's free API along with a short summary of your background, which rates
fit from 0–10. Only postings at or above the threshold get emailed, and each
listed job shows its score.

| Secret | Purpose |
|---|---|
| `GEMINI_API_KEY` | From [aistudio.google.com](https://aistudio.google.com) — free tier, no card required |
| `CV_SUMMARY` | A few sentences describing your background/skills/interests |
| `RELEVANCE_THRESHOLD` | Minimum score 0–10 to include a job (default: 6) |

Leave these three unset and the agent behaves exactly as before — keyword
matching only. If scoring a particular job fails (network hiccup, etc.), that
job is included rather than silently dropped, so a transient API error never
causes a missed opportunity.

## Other possible extensions

- **Multi-source aggregation**: this pattern (fetch → filter → notify)
  generalizes to any API with a timestamp field — RSS feeds, other job
  boards, GitHub release feeds, etc.
- **Persistent dedup**: swap the time-window filter for a small state file
  (e.g. committed back to the repo, or a lightweight hosted key-value store)
  to track exactly which postings have already been sent.

## License

MIT — see [LICENSE](LICENSE).
