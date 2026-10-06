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

## Possible extensions

- **AI relevance scoring**: send each posting's description to a free-tier
  LLM API (e.g. Gemini) along with a CV/profile summary, and only forward
  postings above a relevance threshold — turning keyword matching into actual
  semantic filtering.
- **Multi-source aggregation**: this pattern (fetch → filter → notify)
  generalizes to any API with a timestamp field — RSS feeds, other job
  boards, GitHub release feeds, etc.
- **Persistent dedup**: swap the time-window filter for a small state file
  (e.g. committed back to the repo, or a lightweight hosted key-value store)
  to track exactly which postings have already been sent.

## License

MIT — see [LICENSE](LICENSE).
