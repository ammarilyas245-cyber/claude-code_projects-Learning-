# Dental Practice Lead Finder: Plan (v3, SerpAPI)

Status: code written and typechecked; waiting on API keys for the live test. Not deployed.

v3 replaces Yelp with SerpAPI (Google Maps search) because Yelp's access ends after a 30-day trial.

## 1. Goal
Every Monday at 9:00 AM Pakistan time, find dental practices across the US that are likely to buy a website, and add each one to ClickUp as a task. Practices with no website or an outdated website are the priority.

## 2. Decisions
| Topic | Decision |
|---|---|
| Schedule | Monday 9:00 AM, `Asia/Karachi` time zone (cron `0 9 * * 1`) |
| Lead source | SerpAPI, Google Maps engine (`engine=google_maps`) |
| Delivery | ClickUp, one task per lead, in a "Dental Leads" list |
| Area | Nationwide: 5 of ~50 big US cities per week (10-week pass); optional `LOCATION_OVERRIDE` |
| Volume | ~100 new leads per week (`LEADS_PER_WEEK`) |
| Repeats | Never. The Place ID is stored in each task and checked before creating one; a long-lived idempotency key is a second guard |
| Fields | Name, phone, address, website, email (if findable), rating, review count, Google Maps link, "why it's a fit" |
| Cost | No card. SerpAPI's free tier is limited (250 searches/month as listed on serpapi.com/pricing), NOT unlimited |

## 3. Why SerpAPI works better than Yelp here
- Google Maps results include the practice's own website, so "no website" is reliable (Yelp's cheap plan hid it).
- A typical Monday uses about 5 to 25 searches (20 places per search), so roughly 20 to 100 per month. `SERPAPI_MAX_SEARCHES_PER_RUN` (default 25) caps a run so the free quota can't be burned in one go.
- Paging deeper happens by following SerpAPI's "next page" link until enough new practices are found. After the 10-week city pass, cities are searched deeper automatically, because practices already in ClickUp are skipped.

## 4. Accounts and env vars (names match the tutorial: `SERPAPI_KEY`, `CLICKUP_API_KEY`)
| Variable | Where to get it |
|---|---|
| `TRIGGER_PROJECT_REF` | Trigger.dev dashboard -> Project settings |
| `SERPAPI_KEY` | serpapi.com -> sign up (no card) -> dashboard |
| `CLICKUP_API_KEY` | ClickUp -> avatar -> Settings -> Apps -> API Token |
| `CLICKUP_LIST_ID` | Printed by the `setup-clickup` task |
| Optional | `LEADS_PER_WEEK`, `SERPAPI_MAX_SEARCHES_PER_RUN`, `LOCATION_OVERRIDE` |

After local testing, add the same variables in the Trigger.dev dashboard (Project -> Environment Variables) for staging and prod.

## 5. Files (`src/trigger/dental-leads/`)
- `find-leads.ts`: scheduled orchestrator; picks cities, searches, skips known practices, queues leads.
- `create-lead.ts`: processor; audits the website, finds an email, creates the ClickUp task.
- `setup-clickup.ts`: one-off; creates the "Lead Generation" Space, "Dental Leads" list and tags.
- `lib/`: `serpapi.ts`, `website.ts`, `email.ts`, `clickup.ts`, `cities.ts`, `env.ts`.

## 6. Per-lead processing
- **Website:** none, social/directory page only, dead, outdated (no mobile tag, no HTTPS, copyright 3 or more years old, Flash/frames), or fine.
- **Email:** looked for on the homepage, `/contact` and `/contact-us`; junk filtered; own-domain addresses preferred. No website means no email.
- **ClickUp:** High priority and `website-opportunity` tag for none, social-only, dead or outdated sites; Low for sites that look fine.

## 7. Verified so far
- Typecheck clean; 34 automated checks pass (rotation, website rules, email extraction, SerpAPI parsing and paging with a stubbed network, error handling without leaking keys).

## 8. Not verified until real keys exist
- SerpAPI: that Google Maps paging works from the `next` link as documented, and the free-tier quota for your account.
- ClickUp: free plan API access, Space creation (falls back to "Sales & CRM"), tags on task creation.
- Trigger.dev: acceptance of the 365-day idempotency expiry (ClickUp check is the main guard).
- SerpAPI and Google Maps terms for storing and using this data for outreach: check before relying on it beyond a demo.

## 9. Next steps
1. You: Trigger.dev signup and project ref; SerpAPI key; ClickUp token, all into `.env`.
2. Me: run `setup-clickup`, a real test search, then a local run with `LEADS_PER_WEEK=5`.
3. Review the ClickUp tasks together, then deploy only when you say "deploy".
