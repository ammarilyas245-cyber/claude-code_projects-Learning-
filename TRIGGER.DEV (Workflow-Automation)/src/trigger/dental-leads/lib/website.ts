export type WebsiteStatus =
  | "none" // no website known
  | "social_only" // only a social/directory page, no real site
  | "dead" // does not load
  | "outdated" // loads, but looks old
  | "ok" // loads and looks fine
  | "unknown"; // could not be checked (site blocked the check, or the data source gave no website field)

export interface WebsiteAudit {
  status: WebsiteStatus;
  reasons: string[];
  finalUrl?: string;
  html?: string;
}

const SOCIAL_HOSTS = [
  "facebook.com",
  "instagram.com",
  "yelp.com",
  "linkedin.com",
  "twitter.com",
  "x.com",
  "tiktok.com",
  "youtube.com",
  "linktr.ee",
  "business.site",
  "sites.google.com",
];

const MAX_HTML_CHARS = 500_000;

export function normalizeUrl(raw: string): string | undefined {
  const trimmed = raw.trim();
  if (!trimmed) return undefined;
  const withScheme = /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
  try {
    return new URL(withScheme).toString();
  } catch {
    return undefined;
  }
}

function isSocialHost(hostname: string): boolean {
  const host = hostname.toLowerCase().replace(/^www\./, "");
  return SOCIAL_HOSTS.some((s) => host === s || host.endsWith(`.${s}`));
}

export interface FetchedPage {
  ok: boolean;
  status: number;
  finalUrl: string;
  html: string;
}

/** Fetch a page with a 10 s timeout and one retry on network errors. Returns undefined if unreachable. */
export async function fetchPage(url: string): Promise<FetchedPage | undefined> {
  for (let attempt = 1; attempt <= 2; attempt++) {
    try {
      const res = await fetch(url, {
        redirect: "follow",
        signal: AbortSignal.timeout(10_000),
        headers: {
          "User-Agent": "Mozilla/5.0 (compatible; WebsiteAuditBot/1.0)",
          Accept: "text/html,application/xhtml+xml",
        },
      });
      const contentType = res.headers.get("content-type") ?? "";
      const html = contentType.includes("html") || contentType === "" ? (await res.text()).slice(0, MAX_HTML_CHARS) : "";
      return { ok: res.ok, status: res.status, finalUrl: res.url || url, html };
    } catch {
      // network error, timeout, DNS failure: retry once
    }
  }
  return undefined;
}

/** Latest copyright year mentioned in the page, if any. */
export function latestCopyrightYear(html: string): number | undefined {
  const re = /(?:©|&copy;|&#169;|copyright)[^0-9<]{0,20}(?:(?:19|20)\d{2}\s*[-–—]\s*)?((?:19|20)\d{2})/gi;
  let latest: number | undefined;
  for (const match of html.matchAll(re)) {
    const year = Number(match[1]);
    if (latest === undefined || year > latest) latest = year;
  }
  return latest;
}

/** Pure analysis of a loaded page. Returns the reasons it looks outdated (empty = fine). */
export function outdatedReasons(html: string, finalUrl: string, currentYear: number): string[] {
  const reasons: string[] = [];
  if (!/<meta[^>]+name=["']viewport["']/i.test(html)) reasons.push("not mobile-friendly (no viewport tag)");
  if (finalUrl.toLowerCase().startsWith("http://")) reasons.push("no HTTPS");
  const year = latestCopyrightYear(html);
  if (year !== undefined && currentYear - year >= 3) reasons.push(`copyright year ${year}`);
  if (/<frameset|<embed[^>]+\.swf|application\/x-shockwave-flash/i.test(html)) reasons.push("uses old frames/Flash");
  return reasons;
}

/** Audit a practice's website. `website` is whatever the data source gave us (may be empty). */
export async function auditWebsite(
  website: string | null | undefined,
  websiteFieldKnown: boolean
): Promise<WebsiteAudit> {
  if (!website || !website.trim()) {
    if (!websiteFieldKnown) {
      return { status: "unknown", reasons: ["data source did not return a website field"] };
    }
    return { status: "none", reasons: ["no website listed"] };
  }

  const url = normalizeUrl(website);
  if (!url) return { status: "dead", reasons: ["website address is not a valid URL"] };

  if (isSocialHost(new URL(url).hostname)) {
    return { status: "social_only", reasons: ["only a social/directory page, no real website"], finalUrl: url };
  }

  const page = await fetchPage(url);
  if (!page) return { status: "dead", reasons: ["website did not load"], finalUrl: url };

  if (isSocialHost(new URL(page.finalUrl).hostname)) {
    return { status: "social_only", reasons: ["redirects to a social/directory page"], finalUrl: page.finalUrl };
  }

  if ([401, 403, 429].includes(page.status)) {
    return { status: "unknown", reasons: [`site blocked the automatic check (HTTP ${page.status})`], finalUrl: page.finalUrl };
  }
  if (!page.ok) {
    return { status: "dead", reasons: [`website returns HTTP ${page.status}`], finalUrl: page.finalUrl };
  }

  const reasons = outdatedReasons(page.html, page.finalUrl, new Date().getFullYear());
  return {
    status: reasons.length > 0 ? "outdated" : "ok",
    reasons: reasons.length > 0 ? reasons : ["website looks current"],
    finalUrl: page.finalUrl,
    html: page.html,
  };
}
