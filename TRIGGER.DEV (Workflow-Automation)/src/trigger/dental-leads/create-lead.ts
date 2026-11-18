import { schemaTask } from "@trigger.dev/sdk";
import { z } from "zod";
import { createTask } from "./lib/clickup.js";
import { findEmail } from "./lib/email.js";
import { optionalEnv, requireEnv } from "./lib/env.js";
import { auditWebsite, type WebsiteAudit } from "./lib/website.js";

export const leadSchema = z.object({
  placeId: z.string(),
  name: z.string(),
  mapsUrl: z.string().optional(),
  phone: z.string().optional(),
  address: z.string().optional(),
  /** The search area, for example "Dallas, TX". */
  area: z.string().optional(),
  rating: z.number().optional(),
  reviewCount: z.number().optional(),
  /** The practice's own website from Google Maps (null if none is listed). */
  website: z.string().nullable().optional(),
});

type Lead = z.infer<typeof leadSchema>;

function whyItsAFit(audit: WebsiteAudit): string {
  switch (audit.status) {
    case "none":
      return "No website listed. Strong lead for a brand-new site.";
    case "social_only":
      return "Only a social or directory page, no real website. Strong lead for a new site.";
    case "dead":
      return `Website is broken (${audit.reasons.join(", ")}). Strong lead for a rebuild.`;
    case "outdated":
      return `Website looks outdated: ${audit.reasons.join("; ")}. Good lead for a redesign.`;
    case "ok":
      return "Website looks current. Lower priority.";
    case "unknown":
      return `Website could not be checked: ${audit.reasons.join("; ")}. Review manually.`;
  }
}

function priorityAndTags(audit: WebsiteAudit, hasEmail: boolean): { priority: 2 | 3 | 4; tags: string[] } {
  const tags: string[] = [];
  let priority: 2 | 3 | 4;
  switch (audit.status) {
    case "none":
    case "social_only":
      priority = 2;
      tags.push("website-opportunity", "no-website");
      break;
    case "dead":
      priority = 2;
      tags.push("website-opportunity", "dead-site");
      break;
    case "outdated":
      priority = 2;
      tags.push("website-opportunity", "outdated-site");
      break;
    case "ok":
      priority = 4;
      break;
    case "unknown":
      priority = 3;
      tags.push("website-unchecked");
      break;
  }
  if (hasEmail) tags.push("has-email");
  return { priority, tags };
}

function buildDescription(lead: Lead, audit: WebsiteAudit, email: string | undefined): string {
  const lines = [
    `**Why it's a fit:** ${whyItsAFit(audit)}`,
    "",
    `Practice: ${lead.name}`,
    `Phone: ${lead.phone || "not listed"}`,
    `Address: ${lead.address || "not listed"}`,
    `Website: ${lead.website || "none found"}`,
    `Email: ${email || "not found"}`,
    `Rating: ${lead.rating ?? "n/a"} (${lead.reviewCount ?? 0} reviews)`,
    `Google Maps: ${lead.mapsUrl || "n/a"}`,
    "",
    `Place ID: ${lead.placeId}`,
  ];
  return lines.join("\n");
}

export const createLead = schemaTask({
  id: "create-lead",
  schema: leadSchema,
  retry: { maxAttempts: 3, factor: 2, minTimeoutInMs: 3000, maxTimeoutInMs: 30_000 },
  run: async (lead) => {
    const listId = requireEnv("CLICKUP_LIST_ID");
    requireEnv("CLICKUP_API_KEY");

    // Google Maps lists a website whenever the practice has one, so an empty field means "no website".
    const audit = await auditWebsite(lead.website, true);

    // Look for an email on the practice's own site.
    let email: string | undefined;
    if (audit.html && audit.finalUrl) {
      email = await findEmail(audit.finalUrl, audit.html);
    }

    const { priority, tags } = priorityAndTags(audit, Boolean(email));

    // Test runs are marked ONLY with a tag, so task names and descriptions stay clean.
    if (optionalEnv("TEST_RUN_LABEL")) tags.push("first-test-run");

    const created = await createTask(listId, {
      name: lead.name,
      markdownDescription: buildDescription(lead, audit, email),
      priority,
      tags,
    });

    return { placeId: lead.placeId, taskId: created.id, websiteStatus: audit.status, hasEmail: Boolean(email), priority };
  },
});
