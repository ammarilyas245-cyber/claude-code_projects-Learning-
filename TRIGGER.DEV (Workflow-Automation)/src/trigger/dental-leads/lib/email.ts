import { fetchPage } from "./website.js";

const EMAIL_RE = /[a-z0-9._%+-]+@[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,}/gi;
const FILE_SUFFIX_RE = /\.(png|jpe?g|gif|svg|webp|css|js|ico|woff2?)$/i;
const JUNK_DOMAINS = [
  "example.com",
  "domain.com",
  "yourdomain.com",
  "email.com",
  "sentry.io",
  "wixpress.com",
  "godaddy.com",
  "squarespace.com",
  "wordpress.com",
  "schema.org",
];
const JUNK_LOCALS = ["your", "name", "example", "user", "test", "email", "johndoe", "noreply", "no-reply"];

/** All plausible practice email addresses found in some HTML, best match first. */
export function extractEmails(html: string, siteHost?: string): string[] {
  const decoded = html.replace(/%40/gi, "@").replace(/&#0*64;|&commat;/gi, "@");
  const found = new Set<string>();
  for (const match of decoded.matchAll(EMAIL_RE)) {
    const email = match[0].toLowerCase().replace(/^[.%+-]+/, "");
    const [local = "", domain = ""] = email.split("@");
    if (!local || !domain) continue;
    if (FILE_SUFFIX_RE.test(email)) continue;
    if (JUNK_DOMAINS.some((d) => domain === d || domain.endsWith(`.${d}`))) continue;
    if (JUNK_LOCALS.some((l) => local === l || local.startsWith(`${l}.`))) continue;
    found.add(email);
  }
  const bare = siteHost?.toLowerCase().replace(/^www\./, "");
  return [...found].sort((a, b) => {
    const aOwn = bare && a.endsWith(`@${bare}`) ? 0 : 1;
    const bOwn = bare && b.endsWith(`@${bare}`) ? 0 : 1;
    return aOwn - bOwn;
  });
}

/** Look for an email on the homepage, then /contact and /contact-us. Sequential on purpose. */
export async function findEmail(finalUrl: string, homeHtml: string): Promise<string | undefined> {
  const base = new URL(finalUrl);
  const first = extractEmails(homeHtml, base.hostname)[0];
  if (first) return first;

  for (const path of ["/contact", "/contact-us"]) {
    const page = await fetchPage(new URL(path, base).toString());
    if (page?.ok) {
      const email = extractEmails(page.html, base.hostname)[0];
      if (email) return email;
    }
  }
  return undefined;
}
