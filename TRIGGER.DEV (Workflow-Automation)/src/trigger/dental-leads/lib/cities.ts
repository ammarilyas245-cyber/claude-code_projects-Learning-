export interface City {
  city: string;
  state: string;
}

/** ~50 large US cities. The weekly run takes the next 5 in this list. */
export const CITIES: City[] = [
  { city: "New York", state: "NY" },
  { city: "Los Angeles", state: "CA" },
  { city: "Chicago", state: "IL" },
  { city: "Houston", state: "TX" },
  { city: "Phoenix", state: "AZ" },
  { city: "Philadelphia", state: "PA" },
  { city: "San Antonio", state: "TX" },
  { city: "San Diego", state: "CA" },
  { city: "Dallas", state: "TX" },
  { city: "Jacksonville", state: "FL" },
  { city: "Fort Worth", state: "TX" },
  { city: "Austin", state: "TX" },
  { city: "Charlotte", state: "NC" },
  { city: "Columbus", state: "OH" },
  { city: "Indianapolis", state: "IN" },
  { city: "San Francisco", state: "CA" },
  { city: "Seattle", state: "WA" },
  { city: "Denver", state: "CO" },
  { city: "Washington", state: "DC" },
  { city: "Nashville", state: "TN" },
  { city: "Oklahoma City", state: "OK" },
  { city: "El Paso", state: "TX" },
  { city: "Boston", state: "MA" },
  { city: "Portland", state: "OR" },
  { city: "Las Vegas", state: "NV" },
  { city: "Detroit", state: "MI" },
  { city: "Memphis", state: "TN" },
  { city: "Louisville", state: "KY" },
  { city: "Baltimore", state: "MD" },
  { city: "Milwaukee", state: "WI" },
  { city: "Albuquerque", state: "NM" },
  { city: "Tucson", state: "AZ" },
  { city: "Fresno", state: "CA" },
  { city: "Sacramento", state: "CA" },
  { city: "Kansas City", state: "MO" },
  { city: "Atlanta", state: "GA" },
  { city: "Omaha", state: "NE" },
  { city: "Colorado Springs", state: "CO" },
  { city: "Raleigh", state: "NC" },
  { city: "Miami", state: "FL" },
  { city: "Virginia Beach", state: "VA" },
  { city: "Oakland", state: "CA" },
  { city: "Minneapolis", state: "MN" },
  { city: "Tulsa", state: "OK" },
  { city: "Tampa", state: "FL" },
  { city: "Arlington", state: "TX" },
  { city: "New Orleans", state: "LA" },
  { city: "Wichita", state: "KS" },
  { city: "Cleveland", state: "OH" },
  { city: "Salt Lake City", state: "UT" },
];

export const CITIES_PER_WEEK = 5;

/** First Monday used as week 0 for the rotation. */
const ROTATION_EPOCH_MS = Date.UTC(2026, 0, 5);
const WEEK_MS = 7 * 24 * 60 * 60 * 1000;

export interface WeeklyPlan {
  weekIndex: number;
  cities: City[];
}

/**
 * Pick this week's cities. After a full pass (50 cities / 5 per week = 10 weeks) the list starts
 * over. Practices already in ClickUp are skipped, and the search pages deeper to find new ones,
 * so repeat passes keep producing fresh leads.
 */
export function planWeek(now: Date): WeeklyPlan {
  const weekIndex = Math.max(0, Math.floor((now.getTime() - ROTATION_EPOCH_MS) / WEEK_MS));
  const start = (weekIndex * CITIES_PER_WEEK) % CITIES.length;
  const cities: City[] = [];
  for (let i = 0; i < CITIES_PER_WEEK; i++) {
    const city = CITIES[(start + i) % CITIES.length];
    if (city) cities.push(city);
  }
  return { weekIndex, cities };
}
