// A team's badge letters and colour, made from its name. They are not the real club crests,
// which the project has no right to use.

const SKIP = new Set(["de", "del", "di", "la", "le", "of"]);

export function monogram(name) {
  const words = name.split(/\s+/).filter(
    (w) => !SKIP.has(w.toLowerCase()) && !(w.length <= 3 && w === w.toUpperCase()),
  );
  if (words.length >= 2) return (words[0][0] + words[1][0]).toUpperCase();
  return (words[0] ?? name).slice(0, 3).toUpperCase();
}

export function teamHue(id) {
  let hue = 0;
  for (const ch of id) hue = (hue * 31 + ch.charCodeAt(0)) % 360;
  return hue;
}
