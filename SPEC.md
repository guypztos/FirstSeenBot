# FirstSeen: student job alerts bot (version one spec)

## Goal
A Telegram bot that watches company career feeds and messages me when a student
role in my commute range appears, with a direct link to the company's own posting.
Single user (me) in this version. Telegram bot: t.me/FirstSeenAppBot.

## Roadmap
1. Version one (this spec): documented feeds, `student` profile, single user.
2. Version two:
   - `junior` profile (minimum years of experience extracted from descriptions).
   - More documented sources (Ashby, further Greenhouse and Lever boards).
   - Email-alert adapter for the large employers: the bot reads a dedicated inbox
     that receives the employers' own job-alert emails, and feeds them into the
     same pipeline. See "Compliance rules" for its limits.
3. Only if still needed: grey-area sources (undocumented endpoints such as
   Workday). Gate for each one, all three required before any code:
   the site's terms have been read and do not prohibit automated access,
   robots.txt allows the path, and the decision is recorded in docs/DECISIONS.md.
   Sources whose terms prohibit automation (Amazon, Apple) stay out without
   written permission.

## Sources
The host in a company's job-page URL identifies its system:

| URL host                                        | System     | Status                                   |
|-------------------------------------------------|------------|------------------------------------------|
| jobs.lever.co / jobs.eu.lever.co                | Lever      | Supported in v1                          |
| boards.greenhouse.io / job-boards.greenhouse.io | Greenhouse | Supported in v1                          |
| jobs.ashbyhq.com                                | Ashby      | Documented public feed, version two      |
| comeet.com/jobs                                 | Comeet     | Needs each company's token, later        |
| *.myworkdayjobs.com (Nvidia, Intel)             | Workday    | Undocumented internal endpoint, stage 3  |
| amazon.jobs                                     | custom     | Terms restrict robots. Stays out         |
| jobs.apple.com                                  | custom     | Terms prohibit scraping. Stays out       |
| anything else                                   | custom     | Not until a feed and its terms are confirmed |

### Initial sources.yaml (18 companies, all confirmed live)
- lever_eu: mobileye
- greenhouse: taboola, appsflyer, wizinc, similarweb, riskified, nice, jfrog,
  gongio, payoneer, catonetworks, sentinellabs, lightricks, myheritage, orcasecurity,
  axonius, torq, transmitsecurity

To add a company: open its careers page, click any job, read the host, and add
its slug only if the host is Lever or Greenhouse. The evidence behind this list
is in the appendix.

## Compliance rules (not legal advice; written to keep risk low)
- Sources: only feeds the provider documents as public (Lever Postings API,
  Greenhouse Job Board API, Ashby posting API). Lever's README says published
  postings are publicly viewable and may be scraped by third parties. Greenhouse's
  docs say Job Board data is publicly available and GET needs no authentication.
- Never add a source whose terms prohibit automated access (Amazon, Apple), and
  never an undocumented internal endpoint, without passing the stage 3 gate.
- Never log in, bypass a block, rotate IPs or ignore robots.txt. If a source
  starts refusing requests, stop polling it.
- Polite load: descriptive User-Agent with a contact address, at most one request
  per company per hour, back off on errors.
- Content: descriptions are the employer's text. Store them for matching, but an
  alert shows only the title, key facts, short requirement lines and a link to the
  employer's own page. Do not republish full descriptions.
- Personal data: do not store recruiter names, emails or phone numbers found in
  postings. In v1 the only personal data held is my own chat ID.
- Email-alert adapter (version two): reads only the dedicated bot inbox, never my
  main mailbox. Passes links on as sent and never opens them automatically.
  Personal use only.
- Before opening the bot to other users, add a privacy notice, a delete-my-data
  command, and get the terms and privacy side reviewed by a lawyer.

## Architecture
- One FastAPI service on Google Cloud Run (scales to zero).
- Telegram in webhook mode.
- Cloud Scheduler calls the poll endpoint every 4 hours.
- Postgres on Neon (free plan). Standard Postgres, so it can move to Cloud SQL or RDS later.
- No Redis in this version. Add it when several sources need rate limiting and caching.

## Endpoints
- `POST /telegram/webhook`: bot commands. Reject requests without the
  `X-Telegram-Bot-Api-Secret-Token` header value registered with `setWebhook`.
- `POST /jobs/poll`: called by Cloud Scheduler only. Reject other callers.
- `GET /healthz`: liveness.

## Source adapters
One interface, one class per system:

    fetch_postings(company) -> list[Posting]

`Posting` is the normalised shape: external_id, title, location, team, commitment,
url, created_at, description_text, requirement_lines.

- v1: Lever (global and EU hosts) and Greenhouse. Both are a single documented GET
  returning JSON.
  - Lever: `GET https://api.lever.co/v0/postings/{slug}?mode=json`
    (EU: `https://api.eu.lever.co/...`). Returns a JSON array. Mobileye's is about 1.1 MB.
    Fields: id, text (title), categories {commitment, department, location, team,
    allLocations}, country, workplaceType, createdAt, hostedUrl, applyUrl,
    descriptionPlain, lists, additionalPlain.
  - Greenhouse: `GET https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true`.
    Returns `{jobs: [...], meta: {total}}`. `content=true` includes descriptions.
- Fetch the full board and filter locally. Do not rely on server-side filters:
  Lever's `commitment=Student` filter can miss student roles tagged "Full time".
- Only documented public endpoints. No HTML scraping, no login, no bypassing protections.
- Send a descriptive User-Agent. Never poll one company more than once per hour.

## Profiles
Matching rules are grouped into named profiles so new audiences are a config
change, not new code.
- `student`: built in v1 (rules below).
- `junior`: version two. Titles cannot identify junior roles (see appendix), so it
  needs the minimum years of experience extracted from the description: alert when
  it is 2 or less, or not stated and the title has no Senior/Lead/Principal.
- To make that possible later, v1 stores each posting's plain-text description.

## Matching rules for the `student` profile (config file, not database, in v1)
- Student role: "student", "intern" or "סטודנט" in the title, OR commitment equals "Student".
- Location allowlist: Jerusalem, Tel Aviv, Ramat Gan, Givatayim, Petah Tikva, Herzliya,
  Ra'anana, Kfar Saba, Netanya, and nearby. Haifa is reported but marked "far".
- Exclude list for titles (for example: logistics, operator), editable.
- `requirement_lines`: any line of the description mentioning "semester", "GPA",
  "grade" or "year". Shown in the alert so I can judge eligibility myself.

## Data model
- `companies`: id, name, system (lever | lever_eu | greenhouse), slug, active.
- `postings`: id, company_id, external_id, title, location, team, commitment, url,
  description_text, first_seen_at, last_seen_at, closed_at.
  Unique (company_id, external_id).
- `notifications`: id, posting_id, chat_id, created_at, sent_at. Unique (posting_id, chat_id).
- `poll_runs`: id, company_id, started_at, finished_at, status, fetched_count,
  new_count, error.

## Behaviour
- Poll: for each active company, fetch, upsert postings, update last_seen_at.
- New matching posting: send one Telegram message with title, company, location,
  team, requirement lines and the direct link.
- Closed: a posting missing from a SUCCESSFUL fetch gets closed_at set.
  A failed fetch never closes anything.
- No duplicate alerts: insert the notification row first, send, then set sent_at.
  Unsent rows are retried on the next poll.
- One failing company must not stop the others. Record the error in poll_runs.

## Bot commands
- `/latest`: the 10 most recent open matches.
- `/sources`: each company with its last successful poll time.
- `/status`: last poll summary and any failing sources.

## Security and operations
- Only my chat ID is served. All other senders are ignored.
- Bot token, webhook secret and database URL live in Secret Manager, never in git.
  Locally they come from a `.env` file that is git-ignored.
- Budget alert set on the cloud project before any resource is created.
- Structured logs for every poll run.

## Testing
- Adapters are tested against saved sample responses in `tests/fixtures/`.
  No test makes a real network call.
- Matching rules: table-driven tests, including a "Full time" role with Student in
  the title, a Hebrew title, and a Haifa role.
- Poll logic: new posting, repeated posting, closed posting, failed fetch.

## Out of scope for this version
The junior profile, the email-alert adapter, multiple users, sign-up, a web UI,
Redis, parsing "semesters left" into a number, and any source without a confirmed
public feed.

## Done means
Deployed, polling on schedule, and I have received at least one real alert or a
`/status` showing three consecutive successful polls.

---

## Appendix: source survey findings (2026-11-23 and 2026-11-24)
Background for the decisions above. Not instructions.

### Documented feeds
- Lever: the Mobileye EU feed returned a JSON array without credentials.
  With `&commitment=Student` it returned 3 postings, none of them software
  development roles (logistics, operations control centre, SOC analyst).
- A Mobileye posting page seen on 2026-11-22 was titled "(Student Position)" but
  tagged "Full time", so the commitment filter alone is not reliable.
- Mobileye student developer postings that a web search returned on 2026-11-22 were
  not in the live student feed on 2026-11-23. Search results can show closed roles;
  the feed is the source of truth.
- Greenhouse boards confirmed with Israeli listings: taboola, appsflyer, wizinc,
  similarweb, riskified, nice (Ra'anana), jfrog (Tel Aviv/Netanya), gongio,
  payoneer (Herzliya), catonetworks, sentinellabs, lightricks (Jerusalem),
  orcasecurity, axonius, torq, transmitsecurity.
- Across those 16 boards: about 250 Israel-based jobs and one student role
  (Employer Branding Student at NICE). No student software role.
- Junior check: across four boards with 101 Israel-based jobs, only 2 titles
  contained Junior/Graduate/Entry/Associate, and neither was an engineering role.
- Tokens that did not resolve on Greenhouse: mondaycom, vastdata, radware, cyberark,
  varonis, cellebrite, tipalti, playtika, aquasecurity, snyk, pentera, claroty,
  silverfort. Empty boards: armissecurity, outbraininc. Not found on Ashby: cyera,
  upwind, island. Not found on Lever: cybereason. Find each company's real system
  before adding it.

### Employers without a documented feed
- Amazon: an undocumented search endpoint on amazon.jobs returned 10 student roles
  in Israel without credentials, several of them software roles. Amazon's
  Conditions of Use exclude "data mining, robots, or similar data gathering and
  extraction tools".
- Apple: the jobs.apple.com search page listed 7 student roles in Israel. There is
  no feed, and Apple's Website Terms of Use prohibit page-scraping, robots and spiders.
- Nvidia and Intel: Workday. The career sites call an internal JSON endpoint
  (`/wday/cxs/{tenant}/{site}/jobs`, POST) that is not a documented public API.
  Nvidia's robots.txt allows its career-site path and links a sitemap, but the
  sitemap listed only about 100 URLs and no Israeli student role.
- Microsoft: careers run on Eightfold (apply.careers.microsoft.com). No documented
  public feed found.
- Palo Alto Networks: believed to post through SmartRecruiters, not confirmed.
  SmartRecruiters documents its Posting API as public, but the API host's
  robots.txt refused an automated fetch.
- Own career sites with no feed identified: Elbit (elbitsystemscareer.com),
  Rafael (career.rafael.co.il), KPMG Israel (kpmg.co.il), Amdocs (jobs.amdocs.com),
  Check Point (careers.checkpoint.com). PTC's system was not identified.

### Conclusion
On 2026-11-24 the student roles were concentrated at employers without documented
feeds (Amazon 10, Apple 7), versus 4 non-development student roles on the
documented feeds. Documented-feed coverage therefore suits the junior profile
better than the student profile, and the large employers are covered by their own
email alerts, which the version-two email adapter will read.