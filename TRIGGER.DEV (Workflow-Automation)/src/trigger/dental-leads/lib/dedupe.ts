/**
 * Duplicate detection for leads. A candidate is a duplicate of a lead already in ClickUp
 * (or already picked this run) when ANY of these match:
 *   1. place-id        : same Google Place ID
 *   2. phone-and-name  : same phone number AND same practice name (two listings of one practice)
 *   3. name-and-street : same practice name AND same street address
 * Phone alone is NOT enough: chains and shared buildings can share a number.
 */

export interface LeadFingerprint {
  placeId?: string;
  name: string;
  phone?: string;
  address?: string;
}

export type DuplicateReason = "place-id" | "phone-and-name" | "name-and-street";

/** Last 10 digits of a US phone number, or undefined if it does not look like one. */
export function normalizePhone(raw?: string): string | undefined {
  const digits = (raw ?? "").replace(/\D/g, "");
  const ten = digits.length === 11 && digits.startsWith("1") ? digits.slice(1) : digits;
  return ten.length === 10 ? ten : undefined;
}

export function normalizeName(raw: string): string {
  return raw
    .toLowerCase()
    .replace(/&/g, " and ")
    .replace(/[^a-z0-9 ]/g, " ")
    .replace(/\b(the|of)\b/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

/** Street part of an address without unit/suite numbers, with common abbreviations unified. */
export function normalizeStreet(address?: string): string | undefined {
  if (!address) return undefined;
  const street = (address.split(",")[0] ?? "")
    .toLowerCase()
    .replace(/(#|\bsuite\b|\bste\b|\bunit\b|\bfloor\b|\bfl\b).*$/, "")
    .replace(/[^a-z0-9 ]/g, " ")
    .replace(/\bstreet\b/g, "st")
    .replace(/\bavenue\b/g, "ave")
    .replace(/\broad\b/g, "rd")
    .replace(/\bboulevard\b/g, "blvd")
    .replace(/\bdrive\b/g, "dr")
    .replace(/\s+/g, " ")
    .trim();
  return street || undefined;
}

export class LeadIndex {
  private placeIds = new Set<string>();
  private phoneName = new Set<string>();
  private nameStreet = new Set<string>();

  /** Number of distinct practices recorded. */
  get size(): number {
    return this.placeIds.size;
  }

  add(lead: LeadFingerprint): void {
    const name = normalizeName(lead.name);
    const phone = normalizePhone(lead.phone);
    const street = normalizeStreet(lead.address);
    if (lead.placeId) this.placeIds.add(lead.placeId);
    if (name && phone) this.phoneName.add(`${phone}|${name}`);
    if (name && street) this.nameStreet.add(`${name}|${street}`);
  }

  /** Why this lead is a duplicate, or undefined if it is new. */
  check(lead: LeadFingerprint): DuplicateReason | undefined {
    if (lead.placeId && this.placeIds.has(lead.placeId)) return "place-id";
    const name = normalizeName(lead.name);
    if (!name) return undefined;
    const phone = normalizePhone(lead.phone);
    if (phone && this.phoneName.has(`${phone}|${name}`)) return "phone-and-name";
    const street = normalizeStreet(lead.address);
    if (street && this.nameStreet.has(`${name}|${street}`)) return "name-and-street";
    return undefined;
  }
}

const NEXT_LABEL = "(?=\\s*(?:Why it's a fit:|Practice:|Phone:|Address:|Website:|Email:|Rating:|Google Maps:|Place ID:)|$)";

/** Remove a leading [LABEL] and a trailing ", City, ST" from a ClickUp task name. */
function practiceNameFromTaskName(taskName: string): string {
  return taskName
    .replace(/^\s*\[[^\]]*\]\s*/, "")
    .replace(/\s*,\s*[^,]+,\s*[A-Z]{2}\s*$/, "")
    .trim();
}

/** Read the lead details back out of a ClickUp task (name + the description this automation wrote). */
export function fingerprintFromTask(task: { name?: string; description?: string }): LeadFingerprint | undefined {
  const text = task.description ?? "";
  const placeId = text.match(/Place ID:\s*([A-Za-z0-9_:-]+)/)?.[1];
  const practice = text.match(new RegExp(`Practice:\\s*(.+?)${NEXT_LABEL}`, "s"))?.[1]?.trim();
  const phone = text.match(/Phone:\s*([+()\d][\d\s().+-]{6,20})/)?.[1]?.trim();
  const address = text.match(new RegExp(`Address:\\s*(.+?)${NEXT_LABEL}`, "s"))?.[1]?.trim();
  const name = practice || (task.name ? practiceNameFromTaskName(task.name) : "");
  if (!placeId && !name) return undefined;
  return { placeId, name, phone, address };
}
