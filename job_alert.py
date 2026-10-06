"""
Job Alert Agent — free, no AI needed (but easy to extend with one).

Searches Sweden's official public job board (Arbetsförmedlingen / Platsbanken)
via their free JobSearch API for your chosen keywords, filters to only jobs
published since the last run, and emails you the new matches.

All configuration comes from environment variables (GitHub Actions secrets —
see README.md).
"""

import os
import sys
from datetime import datetime, timedelta, timezone

import requests

# ---------- Config ----------

# Comma-separated search terms, e.g. "data scientist,machine learning,dataanalytiker"
SEARCH_KEYWORDS = [k.strip() for k in os.environ["SEARCH_KEYWORDS"].split(",") if k.strip()]

# Optional: comma-separated Arbetsförmedlingen municipality codes to restrict location,
# e.g. "0780" for Växjö. Leave unset / blank to search all of Sweden.
MUNICIPALITIES = [m.strip() for m in os.environ.get("MUNICIPALITIES", "").split(",") if m.strip()]

# How many hours back to look for "new" postings. Should be a bit more than your
# schedule's interval (e.g. 36 for a daily run) so nothing slips through the gap.
LOOKBACK_HOURS = int(os.environ.get("LOOKBACK_HOURS", "36"))

RESEND_API_KEY = os.environ["RESEND_API_KEY"]
TO_EMAIL = os.environ["TO_EMAIL"]

API_URL = "https://jobsearch.api.jobtechdev.se/search"


def fetch_jobs_for_keyword(keyword: str) -> list[dict]:
    params = {"q": keyword, "limit": 30, "sort": "pubdate-desc"}
    if MUNICIPALITIES:
        params["municipality"] = MUNICIPALITIES
    resp = requests.get(API_URL, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json().get("hits", [])


def is_recent(hit: dict, cutoff: datetime) -> bool:
    pub = hit.get("publication_date")
    if not pub:
        return False
    try:
        pub_dt = datetime.fromisoformat(pub)
    except ValueError:
        return False
    if pub_dt.tzinfo is None:
        pub_dt = pub_dt.replace(tzinfo=timezone.utc)
    return pub_dt >= cutoff


def collect_new_jobs() -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    seen_ids = set()
    results = []

    for keyword in SEARCH_KEYWORDS:
        for hit in fetch_jobs_for_keyword(keyword):
            job_id = hit.get("id")
            if job_id in seen_ids:
                continue
            if not is_recent(hit, cutoff):
                continue
            seen_ids.add(job_id)
            results.append(hit)

    results.sort(key=lambda h: h.get("publication_date", ""), reverse=True)
    return results


def format_job(hit: dict) -> str:
    title = hit.get("headline", "Untitled role")
    employer = (hit.get("employer") or {}).get("name", "Unknown employer")
    addr = hit.get("workplace_address") or {}
    location = addr.get("municipality") or addr.get("city") or "Location not specified"
    deadline = hit.get("application_deadline", "")
    if deadline:
        deadline = deadline.split("T")[0]
    url = hit.get("webpage_url", "")

    lines = [f"{title} — {employer}", f"{location}"]
    if deadline:
        lines.append(f"Apply by: {deadline}")
    lines.append(url)
    return "\n".join(lines)


def build_email_body(jobs: list[dict]) -> str:
    today_str = datetime.now(timezone.utc).strftime("%A, %B %-d")
    header = [f"Job Alert — {today_str}", "=" * 40, ""]

    if not jobs:
        header.append(f"No new postings matching your keywords in the last {LOOKBACK_HOURS} hours.")
        return "\n".join(header)

    header.append(f"{len(jobs)} new match(es):\n")
    body = "\n\n".join(format_job(j) for j in jobs)
    return "\n".join(header) + body


def send_email(subject: str, body: str) -> None:
    resp = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "from": "Job Alert <onboarding@resend.dev>",
            "to": [TO_EMAIL],
            "subject": subject,
            "text": body,
        },
        timeout=15,
    )
    resp.raise_for_status()


def main() -> None:
    try:
        jobs = collect_new_jobs()
        body = build_email_body(jobs)
        print(body)
        subject = f"Job Alert — {len(jobs)} new match(es)" if jobs else "Job Alert — no new matches today"
        send_email(subject, body)
        print("\nAlert sent successfully.")
    except Exception as exc:
        print(f"Failed to build/send job alert: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
