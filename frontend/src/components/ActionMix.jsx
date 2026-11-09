// What a player does with the ball: the share of their decisions that are passes, carries and so on,
// as bars, with a tick for a typical player in the same position.
import { motion } from "motion/react";
import { pct } from "../lib/format";

export const ACTION_NAMES = {
  pass: "Passes", carry: "Carries", dribble: "Dribbles", shot: "Shots", loss: "Ball losses", clear: "Clearances",
};

export default function ActionMix({ actions, name, typical }) {
  const max = Math.max(...actions.flatMap((a) => [a.share, a.position_average]));
  const at = (v) => `${(v / max) * 100}%`;
  return (
    <figure>
      <figcaption className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-mist">
        <span className="inline-flex items-center gap-2"><span className="h-2.5 w-4 rounded-[3px] bg-chart" />{name}</span>
        <span className="inline-flex items-center gap-2"><span className="h-3.5 w-0.5 rounded bg-chalk" />{typical}</span>
      </figcaption>
      <table className="mt-4 w-full border-separate border-spacing-y-2 text-sm">
        <thead className="sr-only">
          <tr><th>Action</th><th>Bar</th><th>{name}</th><th>{typical}</th></tr>
        </thead>
        <tbody>
          {actions.map((a) => (
            <tr key={a.action}>
              <th scope="row" className="w-24 pr-3 text-left font-normal text-mist">{ACTION_NAMES[a.action] ?? a.action}</th>
              <td className="relative h-6" aria-hidden>
                <motion.span className="absolute inset-y-1 left-0 rounded-r-[4px] bg-chart" initial={{ width: 0 }}
                             animate={{ width: at(a.share) }} transition={{ duration: 0.7, ease: "easeOut" }} />
                <span className="absolute inset-y-0 w-0.5 -translate-x-1/2 rounded bg-chalk" style={{ left: at(a.position_average) }} />
              </td>
              <td className="tabular w-16 pl-3 text-right">{pct(a.share)}</td>
              <td className="tabular w-16 pl-2 text-right text-fog">{pct(a.position_average)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}

const VERBS = {
  pass: "Passes", carry: "Carries the ball", dribble: "Dribbles", shot: "Shoots", loss: "Loses the ball", clear: "Clears the ball",
};

// The clearest differences from a typical player in the same position, in words. Differences
// under 20% are left out, and so are actions a typical player almost never takes.
export function styleNotes(actions, positionName) {
  const compared = actions
    .filter((a) => a.position_average >= 0.005)
    .map((a) => ({ ...a, ratio: a.share / a.position_average }));
  const more = compared.filter((a) => a.ratio >= 1.2).sort((a, b) => b.ratio - a.ratio).slice(0, 2);
  const less = compared.filter((a) => a.ratio <= 0.8).sort((a, b) => a.ratio - b.ratio).slice(0, 2);
  return [
    ...more.map((a) => ({ key: a.action, more: true,
      text: `${VERBS[a.action]} on ${pct(a.share)} of decisions, ${a.ratio.toFixed(1)} times as often as a typical ${positionName}` })),
    ...less.map((a) => ({ key: a.action, more: false,
      text: `${VERBS[a.action]} on ${pct(a.share)} of decisions, against ${pct(a.position_average)} for a typical ${positionName}` })),
  ];
}
