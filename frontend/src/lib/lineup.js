// Where each StatsBomb role stands in a formation, in pitch yards with the team attacking to the
// right: x runs from its own goal (0) to the opponent's (120), y from its left touchline (0) to its
// right (80). This matches the API's coordinates, where right backs average y = 69.

export const ROLE_SPOTS = {
  "Goalkeeper": [7, 40],
  "Left Back": [27, 10],
  "Left Center Back": [23, 28],
  "Center Back": [23, 40],
  "Right Center Back": [23, 52],
  "Right Back": [27, 70],
  "Left Wing Back": [38, 8],
  "Right Wing Back": [38, 72],
  "Left Defensive Midfield": [41, 31],
  "Center Defensive Midfield": [41, 40],
  "Right Defensive Midfield": [41, 49],
  "Left Midfield": [58, 10],
  "Left Center Midfield": [55, 28],
  "Center Midfield": [55, 40],
  "Right Center Midfield": [55, 52],
  "Right Midfield": [58, 70],
  "Left Attacking Midfield": [70, 27],
  "Center Attacking Midfield": [70, 40],
  "Right Attacking Midfield": [70, 53],
  "Left Wing": [80, 12],
  "Right Wing": [80, 68],
  "Secondary Striker": [84, 40],
  "Left Center Forward": [92, 31],
  "Center Forward": [94, 40],
  "Striker": [94, 40],
  "Right Center Forward": [92, 49],
};

const LINE_X = { GK: 7, DEF: 25, MID: 52, FWD: 88 };
const SPREAD = 12;   // yards between players who share a spot

// Give each player a spot: their usual role's, or a place on their position's line when the role
// is unknown. Players who share a spot are moved apart vertically.
export function placeEleven(players) {
  const spots = players.map((p) => ROLE_SPOTS[p.role] ?? null);
  const unplaced = {};
  players.forEach((p, i) => {
    if (!spots[i]) (unplaced[p.position] ??= []).push(i);
  });
  for (const [line, members] of Object.entries(unplaced)) {
    members.forEach((i, k) => {
      spots[i] = [LINE_X[line] ?? LINE_X.MID, (80 * (k + 1)) / (members.length + 1)];
    });
  }
  const shared = new Map();
  spots.forEach(([x, y], i) => shared.set(`${x},${y}`, [...(shared.get(`${x},${y}`) ?? []), i]));
  for (const members of shared.values()) {
    members.forEach((i, k) => {
      const [x, y] = spots[i];
      const offset = (k - (members.length - 1) / 2) * SPREAD;
      spots[i] = [x, Math.min(76, Math.max(4, y + offset))];
    });
  }
  return players.map((p, i) => ({ ...p, x: spots[i][0], y: spots[i][1] }));
}
