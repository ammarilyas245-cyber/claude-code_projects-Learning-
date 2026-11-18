import { requireEnv, sleep } from "./env.js";

const SERPAPI_URL = "https://serpapi.com/search.json";

export interface SerpPlace {
  title?: string;
  place_id?: string;
  data_id?: string;
  address?: string;
  phone?: string;
  /** The practice's own website, exactly as listed on Google Maps. Absent when none is listed. */
  website?: string;
  rating?: number;
  reviews?: number;
  type?: string;
  types?: string[];
  open_state?: string;
}

export interface SerpPage {
  places: SerpPlace[];
  /** SerpApi's link to the next page of the same search (undefined on the last page). */
  nextUrl?: string;
}

interface SerpResponse {
  local_results?: SerpPlace[];
  error?: string;
  serpapi_pagination?: { next?: string };
}

async function fetchSerp(url: URL): Promise<SerpPage> {
  url.searchParams.set("api_key", requireEnv("SERPAPI_KEY"));

  for (let attempt = 1; attempt <= 3; attempt++) {
    const res = await fetch(url);
    // 429 can mean a short rate limit OR an exhausted monthly quota. Retry briefly, then give up.
    if (res.status === 429 && attempt < 3) {
      await sleep(3000 * attempt);
      continue;
    }
    const body = (await res.json().catch(() => ({}))) as SerpResponse;
    if (!res.ok) {
      throw new Error(`SerpApi failed with HTTP ${res.status}: ${String(body.error ?? "no details").slice(0, 200)}`);
    }
    if (body.error) {
      // SerpApi reports "no results" as an error message on a 200 response.
      if (/hasn't returned any results|no results/i.test(body.error)) return { places: [] };
      throw new Error(`SerpApi error: ${body.error.slice(0, 200)}`);
    }
    return { places: body.local_results ?? [], nextUrl: body.serpapi_pagination?.next };
  }
  throw new Error("SerpApi failed after retries");
}

/** First page (up to 20 places) of a Google Maps search, for example "dentist in Dallas, TX". */
export function searchMaps(query: string): Promise<SerpPage> {
  const url = new URL(SERPAPI_URL);
  url.searchParams.set("engine", "google_maps");
  url.searchParams.set("type", "search");
  url.searchParams.set("q", query);
  url.searchParams.set("hl", "en");
  url.searchParams.set("gl", "us");
  return fetchSerp(url);
}

/** Follow the `nextUrl` returned by a previous page. */
export function searchMapsNext(nextUrl: string): Promise<SerpPage> {
  return fetchSerp(new URL(nextUrl));
}

const DENTAL_TYPE_RE = /dent|orthodont|periodont|endodont|oral surg|prosthodont/i;

/** Google Maps text searches can return non-dental places. Keep only dental practices. */
export function isDentalPlace(place: SerpPlace): boolean {
  return [place.type, ...(place.types ?? [])].some((t) => typeof t === "string" && DENTAL_TYPE_RE.test(t));
}

export function isClosedPlace(place: SerpPlace): boolean {
  return /permanently closed/i.test(place.open_state ?? "");
}

/** Stable ID for a practice. Used to make sure it is never added twice. */
export function placeKey(place: SerpPlace): string | undefined {
  return place.place_id ?? place.data_id;
}
