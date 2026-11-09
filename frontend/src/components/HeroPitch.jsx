// The home page picture: a passing move drawn on a pitch, with the ball travelling along it.
// The positions are made up for illustration; real matches come from the simulator.
// The players are always visible; only the line and the ball move, so the picture is complete
// even before any animation runs.
import { motion, useReducedMotion } from "motion/react";
import Pitch from "./Pitch";

const MOVE = [[28, 52], [44, 30], [61, 44], [78, 22], [97, 34], [108, 41]];
const DEFENDERS = [[70, 33], [86, 30], [94, 45], [101, 26], [104, 52]];
const PATH = MOVE.map(([x, y], i) => `${i ? "L" : "M"} ${x} ${y}`).join(" ");

export default function HeroPitch() {
  const reduce = useReducedMotion();
  return (
    <Pitch className="w-full drop-shadow-[0_30px_60px_rgb(0_0_0/0.45)]" title="A passing move on a pitch">
      <motion.path d={PATH} fill="none" strokeWidth="0.6" strokeLinecap="round" className="stroke-gold/70"
                   initial={reduce ? false : { pathLength: 0 }} animate={{ pathLength: 1 }}
                   transition={{ duration: 2.4, ease: "easeInOut" }} />
      {MOVE.map(([x, y]) => (
        <g key={`${x}-${y}`}>
          <circle cx={x} cy={y} r="2.6" className="fill-home/20" />
          <circle cx={x} cy={y} r="1.5" className="fill-home stroke-pitch-950" strokeWidth="0.4" />
        </g>
      ))}
      {DEFENDERS.map(([x, y]) => (
        <circle key={`${x}-${y}`} cx={x} cy={y} r="1.5" className="fill-away/80 stroke-pitch-950" strokeWidth="0.4" />
      ))}
      {reduce ? (
        <circle cx={MOVE.at(-1)[0] + 3} cy={MOVE.at(-1)[1]} r="1.1" className="fill-chalk" />
      ) : (
        <motion.circle r="1.1" className="fill-chalk"
                       initial={{ cx: MOVE[0][0], cy: MOVE[0][1] }}
                       animate={{ cx: MOVE.map((p) => p[0]), cy: MOVE.map((p) => p[1]) }}
                       transition={{ duration: 3.2, ease: "easeInOut", repeat: Infinity, repeatDelay: 1.2 }} />
      )}
    </Pitch>
  );
}
