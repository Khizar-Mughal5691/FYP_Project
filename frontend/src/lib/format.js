// Number and name formats shared by the screens.

// 0.0589 -> "5.9%". A share too small to show at this precision is "<0.1%", not "0.0%".
export function pct(x, digits = 1) {
  if (x == null) return "–";
  const smallest = 10 ** -digits;
  if (x > 0 && x * 100 < smallest / 2) return `<${smallest.toFixed(digits)}%`;
  return `${(x * 100).toFixed(digits)}%`;
}

export const fixed = (x, digits = 1) => (x == null ? "–" : x.toFixed(digits));

export const count = (n) => (n == null ? "–" : n.toLocaleString("en-US"));

export function ordinal(n) {
  const lastTwo = n % 100;
  const suffix = lastTwo >= 11 && lastTwo <= 13 ? "th" : ({ 1: "st", 2: "nd", 3: "rd" }[n % 10] ?? "th");
  return `${n}${suffix}`;
}

// Lower case without accents, for searching: "Atlético" matches "atletico".
export const plain = (text) => (text ?? "").normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase().trim();

export const POSITION_NAMES ={ GK: "goalkeeper", DEF: "defender", MID: "midfielder", FWD: "forward" };

export const LEAGUES = [
  { id: "premier_league", name: "Premier League" },
  { id: "la_liga", name: "La Liga" },
  { id: "serie_a", name: "Serie A" },
  { id: "ligue_1", name: "Ligue 1" },
];

// "Lionel Messi" -> "Messi", "Kevin De Bruyne" -> "De Bruyne": the name printed under a player on
// a pitch, where there is room for one word or a surname with its particle.
const PARTICLES = new Set(["de", "da", "das", "do", "dos", "di", "del", "della", "van", "von", "der", "den", "ter", "le", "la", "du", "el", "al", "ben", "mac"]);

export function pitchName(name) {
  const words = (name ?? "").trim().split(/\s+/);
  if (words.length < 2) return words[0] ?? "";
  const last = words.at(-1);
  const before = words.at(-2);
  return PARTICLES.has(before.toLowerCase()) ? `${before} ${last}` : last;
}
