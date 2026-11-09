// A team's eight profile numbers. Each meter shows where the team ranks among all 80 teams: a full
// meter is the best of the four leagues, whether "best" means the highest or the lowest value.
import { motion } from "motion/react";
import { ordinal, pct } from "../lib/format";

const METRICS = {
  att_pass: { title: "Pass completion", format: (v) => pct(v) },
  att_shot: { title: "Shots", format: (v) => pct(v, 2) },
  att_loss: { title: "Ball losses", format: (v) => pct(v) },
  def_pass: { title: "Opponents' pass completion", format: (v) => pct(v) },
  def_shot: { title: "Opponents' shots", format: (v) => pct(v, 2) },
  def_loss: { title: "Ball losses forced", format: (v) => pct(v) },
  def_press: { title: "Pressure on opponents", format: (v) => pct(v) },
  press_factor: { title: "Pressing intensity", format: (v) => `${v.toFixed(2)}×` },
};

const GROUPS = [
  { title: "With the ball", keys: ["att_pass", "att_shot", "att_loss"] },
  { title: "Without the ball", keys: ["def_pass", "def_shot", "def_loss", "def_press", "press_factor"] },
];

export const metricTitle = (key) => METRICS[key]?.title ?? key;
export const formatMetric = (key, value) => (METRICS[key]?.format ?? ((v) => v.toFixed(3)))(value);

// 1 for the best of the teams, 0 for the worst.
export const standing = (n) => (n.out_of - n.rank) / (n.out_of - 1);

export default function ProfileMeters({ profile }) {
  const byKey = Object.fromEntries(profile.map((n) => [n.key, n]));
  return (
    <div className="flex flex-col gap-7">
      {GROUPS.map((group) => (
        <section key={group.title} aria-label={group.title}>
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-[0.16em] text-fog">{group.title}</h3>
          <ul className="flex flex-col gap-5">
            {group.keys.filter((k) => byKey[k]).map((k) => <Meter key={k} n={byKey[k]} />)}
          </ul>
        </section>
      ))}
    </div>
  );
}

function Meter({ n }) {
  const filled = Math.max(standing(n) * 100, 1.5);
  return (
    <li>
      <div className="flex items-baseline justify-between gap-3">
        <span className="font-semibold">{metricTitle(n.key)}</span>
        <span className="tabular shrink-0 text-sm">{formatMetric(n.key, n.value)}</span>
      </div>
      <div role="meter" aria-label={`${metricTitle(n.key)} rank`} aria-valuemin={1} aria-valuemax={n.out_of}
           aria-valuenow={n.out_of - n.rank + 1} aria-valuetext={`${ordinal(n.rank)} of ${n.out_of} teams`}
           className="mt-2 h-2 rounded-full bg-chart/20">
        <motion.div className="h-full rounded-full bg-chart" initial={{ width: 0 }} animate={{ width: `${filled}%` }}
                    transition={{ duration: 0.8, ease: "easeOut" }} />
      </div>
      <div className="mt-1.5 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-0.5 text-xs text-fog">
        <span>{n.label === metricTitle(n.key) ? "" : `${n.label}. `}{n.better === "higher" ? "Higher" : "Lower"} is better</span>
        <span className="tabular">
          <span className="font-semibold text-chalk">{ordinal(n.rank)}</span> of {n.out_of} · average {formatMetric(n.key, n.league_average)}
        </span>
      </div>
    </li>
  );
}
