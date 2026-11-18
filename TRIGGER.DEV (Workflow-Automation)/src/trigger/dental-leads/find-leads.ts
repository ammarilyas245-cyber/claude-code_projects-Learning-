import { idempotencyKeys, schedules } from "@trigger.dev/sdk";
import { createLead } from "./create-lead.js";
import { CITIES_PER_WEEK, planWeek } from "./lib/cities.js";
import { getExistingLeadIndex } from "./lib/clickup.js";
import type { DuplicateReason, LeadIndex } from "./lib/dedupe.js";
import { optionalEnv, requireEnv } from "./lib/env.js";
import {
  isClosedPlace,
  isDentalPlace,
  placeKey,
  searchMaps,
  searchMapsNext,
  type SerpPage,
  type SerpPlace,
} from "./lib/serpapi.js";

/** Remember a practice for a year so it is never queued twice. ClickUp is checked too. */
const IDEMPOTENCY_TTL = "365d";

/** SerpApi's free plan has a monthly search quota, so every run counts and caps its searches. */
const DEFAULT_MAX_SEARCHES_PER_RUN = 25;
const MAX_PAGES_PER_CITY = 12;

interface Budget {
  used: number;
  max: number;
}

interface Candidate {
  place: SerpPlace;
  placeId: string;
  area: string;
}

/** How many found practices were dropped as duplicates, by the reason they matched. */
type DuplicateStats = Record<DuplicateReason, number>;

/**
 * Collect up to `target` NEW dental practices for one location, paging deeper into the
 * Google Maps results until enough new ones are found or the search budget runs out.
 * A practice that matches one already in ClickUp (or already picked this run) is dropped.
 */
async function collectNew(
  area: string,
  target: number,
  index: LeadIndex,
  budget: Budget,
  duplicates: DuplicateStats
): Promise<Candidate[]> {
  const found: Candidate[] = [];
  let page: SerpPage | undefined;

  for (let i = 0; i < MAX_PAGES_PER_CITY && found.length < target; i++) {
    if (budget.used >= budget.max) break;
    budget.used++;
    page = i === 0 || !page?.nextUrl ? await searchMaps(`dentist in ${area}`) : await searchMapsNext(page.nextUrl);
    if (i > 0 && page.places.length === 0) break;

    for (const place of page.places) {
      if (found.length >= target) break;
      const placeId = placeKey(place);
      if (!placeId || !place.title) continue;
      if (!isDentalPlace(place) || isClosedPlace(place)) continue;

      const fingerprint = { placeId, name: place.title, phone: place.phone, address: place.address };
      const reason = index.check(fingerprint);
      if (reason) {
        duplicates[reason]++;
        continue;
      }
      index.add(fingerprint);
      found.push({ place, placeId, area });
    }
    if (!page.nextUrl) break;
  }
  return found;
}

function toPayload({ place, placeId, area }: Candidate) {
  return {
    placeId,
    name: place.title ?? "Unknown practice",
    mapsUrl: `https://www.google.com/maps/place/?q=place_id:${placeId}`,
    phone: place.phone || undefined,
    address: place.address || undefined,
    area,
    rating: place.rating,
    reviewCount: place.reviews,
    website: place.website || null,
  };
}

/** Every Monday at 9:00 AM Pakistan time. */
export const findLeads = schedules.task({
  id: "find-leads",
  cron: { pattern: "0 9 * * 1", timezone: "Asia/Karachi" },
  run: async (payload) => {
    requireEnv("SERPAPI_KEY");
    requireEnv("CLICKUP_API_KEY");
    const listId = requireEnv("CLICKUP_LIST_ID");
    const leadsPerWeek = Number(optionalEnv("LEADS_PER_WEEK") ?? "100");
    if (!Number.isInteger(leadsPerWeek) || leadsPerWeek < 1) {
      throw new Error("LEADS_PER_WEEK must be a whole number of 1 or more");
    }
    const maxSearches = Number(optionalEnv("SERPAPI_MAX_SEARCHES_PER_RUN") ?? DEFAULT_MAX_SEARCHES_PER_RUN);
    if (!Number.isInteger(maxSearches) || maxSearches < 1) {
      throw new Error("SERPAPI_MAX_SEARCHES_PER_RUN must be a whole number of 1 or more");
    }
    const override = optionalEnv("LOCATION_OVERRIDE");

    // Practices already in ClickUp (open, closed or archived) are never added again.
    const index = await getExistingLeadIndex(listId);
    const alreadyInClickUp = index.size;
    const duplicates: DuplicateStats = { "place-id": 0, "phone-and-name": 0, "name-and-street": 0 };

    const week = planWeek(payload.timestamp);
    const searches = override
      ? [{ area: override, target: leadsPerWeek }]
      : week.cities.map((c) => ({
          area: `${c.city}, ${c.state}`,
          target: Math.ceil(leadsPerWeek / CITIES_PER_WEEK),
        }));

    const budget: Budget = { used: 0, max: maxSearches };
    const candidates: Candidate[] = [];
    const perLocation: Record<string, number> = {};
    for (const search of searches) {
      const found = await collectNew(search.area, search.target, index, budget, duplicates);
      perLocation[search.area] = found.length;
      candidates.push(...found);
    }

    // One processor run per practice. Sequential on purpose (no Promise.all).
    let queued = 0;
    for (const candidate of candidates.slice(0, leadsPerWeek)) {
      const idempotencyKey = await idempotencyKeys.create(`place-${candidate.placeId}`, { scope: "global" });
      await createLead.trigger(toPayload(candidate), { idempotencyKey, idempotencyKeyTTL: IDEMPOTENCY_TTL });
      queued++;
    }

    return {
      weekIndex: week.weekIndex,
      mode: override ? "override" : "rotation",
      perLocation,
      alreadyInClickUp,
      duplicatesRemoved: duplicates["place-id"] + duplicates["phone-and-name"] + duplicates["name-and-street"],
      duplicatesByReason: duplicates,
      searchesUsed: budget.used,
      searchBudget: budget.max,
      candidatesFound: candidates.length,
      queued,
    };
  },
});
