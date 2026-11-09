// Small API responses in the shapes of docs/api.md, for the tests.

const ref = (id, name, league, league_name) => ({ id, name, league, league_name });

export const BARCELONA = ref("barcelona", "Barcelona", "la_liga", "La Liga");
export const ATLETICO = ref("atletico-madrid", "Atlético Madrid", "la_liga", "La Liga");
export const ARSENAL = ref("arsenal", "Arsenal", "premier_league", "Premier League");
export const LEICESTER = ref("leicester-city", "Leicester City", "premier_league", "Premier League");
export const JUVENTUS = ref("juventus", "Juventus", "serie_a", "Serie A");

export const TEAMS = [ARSENAL, LEICESTER, ATLETICO, BARCELONA, JUVENTUS];

const number = (key, value, average, better, rank) => ({
  key, label: key, value, league_average: average, better, rank, out_of: 80,
});

const player = (player_id, short_name, name, position, role, num, starts, decisions) => ({
  player_id, short_name, name, position, role, number: num, starts, matches: starts + 2, decisions,
});

const ELEVEN = [
  player(20055, "Marc-André ter Stegen", "Marc-André ter Stegen", "GK", "Goalkeeper", 1, 8, 400),
  player(5211, "Jordi Alba", "Jordi Alba Ramos", "DEF", "Left Back", 18, 20, 1500),
  player(5213, "Gerard Piqué", "Gerard Piqué Bernabéu", "DEF", "Left Center Back", 3, 21, 1600),
  player(5492, "Javier Mascherano", "Javier Alejandro Mascherano", "DEF", "Right Center Back", 14, 19, 1400),
  player(6374, "Dani Alves", "Daniel Alves da Silva", "DEF", "Right Back", 22, 17, 1450),
  player(5203, "Sergio Busquets", "Sergio Busquets i Burgos", "MID", "Center Defensive Midfield", 5, 22, 1900),
  player(5470, "Ivan Rakitić", "Ivan Rakitić", "MID", "Right Center Midfield", 4, 20, 1700),
  player(5216, "Andrés Iniesta", "Andrés Iniesta Luján", "MID", "Left Center Midfield", 8, 16, 1550),
  player(5503, "Lionel Messi", "Lionel Andrés Messi Cuccittini", "FWD", "Right Wing", 10, 18, 2186),
  player(5246, "Luis Suárez", "Luis Alberto Suárez Díaz", "FWD", "Center Forward", 9, 21, 1455),
  player(5470 + 1, "Neymar", "Neymar da Silva Santos Junior", "FWD", "Left Wing", 11, 20, 1800),
];

export const TEAM = {
  ...BARCELONA,
  formation: "4-3-3",
  profile: [
    { ...number("att_pass", 0.8547, 0.7726, "higher", 2), label: "Pass completion" },
    number("att_shot", 0.0161, 0.0119, "higher", 4),
    number("att_loss", 0.0301, 0.0392, "lower", 9),
    number("def_pass", 0.7012, 0.7726, "lower", 5),
    number("def_shot", 0.0128, 0.0119, "lower", 61),
    number("def_loss", 0.0391, 0.0392, "higher", 40),
    number("def_press", 0.2101, 0.1952, "higher", 12),
    number("press_factor", 1.0712, 1.0, "higher", 7),
  ],
  usual_xi: ELEVEN.map(({ starts, matches, decisions, ...p }) => p),
  squad: [
    ...ELEVEN,
    player(5477, "Arda Turan", "Arda Turan", "MID", null, 7, 0, 210),
  ],
  credit: "Data: StatsBomb open data, 2015/16 season, used for non-commercial research.",
};

const touch = [
  0.000, 0.004, 0.010, 0.020, 0.030, 0.012,
  0.000, 0.006, 0.020, 0.050, 0.090, 0.060,
  0.000, 0.008, 0.040, 0.110, 0.180, 0.090,
  0.000, 0.004, 0.030, 0.070, 0.120, 0.046,
];

export const PLAYER = {
  player_id: 5503,
  name: "Lionel Andrés Messi Cuccittini",
  short_name: "Lionel Messi",
  position: "FWD",
  teams: [{ ...BARCELONA, number: 10, role: "Right Wing", starts: 15, matches: 17, decisions: 2186 }],
  actions: [
    { action: "pass", share: 0.5812, position_average: 0.5521 },
    { action: "carry", share: 0.2741, position_average: 0.2894 },
    { action: "dribble", share: 0.0589, position_average: 0.037 },
    { action: "shot", share: 0.0472, position_average: 0.0391 },
    { action: "loss", share: 0.0346, position_average: 0.0612 },
    { action: "clear", share: 0.004, position_average: 0.0212 },
  ],
  involvement: { decisions_per_match: 116.81, position_average: 50.05 },
  touch_map: {
    columns: 6, rows: 4, zone_size_yards: [20, 20],
    values: touch,
    position_average: touch.map((v, i) => (i % 6 === 4 ? v * 0.6 : v * 1.1)),
  },
  credit: "Data: StatsBomb open data, 2015/16 season, used for non-commercial research.",
};

const row = (player_id, short_name, name, position, team, num, matches, perMatch) => ({
  player_id, short_name, name, position, number: num, role: null, team,
  starts: matches, matches, decisions: Math.round(matches * perMatch), decisions_per_match: perMatch,
});

export const MESSI_ROW = row(5503, "Lionel Messi", "Lionel Andrés Messi Cuccittini", "FWD", BARCELONA, 10, 17, 116.81);
export const BUFFON_ROW = row(20000, "Gianluigi Buffon", "Gianluigi Buffon", "GK", JUVENTUS, 1, 21, 31.2);
