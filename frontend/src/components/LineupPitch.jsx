// A team's eleven on a pitch, attacking to the right. Each player is a link to their profile.
import { Link } from "react-router";
import { pitchName, POSITION_NAMES } from "../lib/format";
import { placeEleven } from "../lib/lineup";
import Pitch from "./Pitch";

export default function LineupPitch({ players, title, className }) {
  const placed = placeEleven(players);
  return (
    <Pitch className={className} title={title} role="group">
      <text x="60" y="83.2" textAnchor="middle" className="fill-fog text-[2.6px] font-semibold uppercase tracking-[0.3em]">
        Attacking direction →
      </text>
      {placed.map((p) => (
        <Link key={p.player_id} to={`/players/${p.player_id}`} className="group outline-none"
              aria-label={`${p.short_name}, ${p.role ?? POSITION_NAMES[p.position]}`}>
          <circle cx={p.x} cy={p.y} r="6.5" className="fill-transparent" />
          <circle cx={p.x} cy={p.y} r="4.4" strokeWidth="0.7"
                  className="fill-chart-home stroke-pitch-950 transition-colors group-hover:fill-home group-focus-visible:fill-gold" />
          <text x={p.x} y={p.y} dy="0.36em" textAnchor="middle" className="fill-pitch-950 text-[3.3px] font-semibold">
            {p.number ?? p.position}
          </text>
          <text x={p.x} y={p.y + 8} textAnchor="middle" strokeWidth="0.9" style={{ paintOrder: "stroke" }}
                className="fill-chalk stroke-pitch-900 text-[3.2px] font-semibold group-hover:fill-gold">
            {pitchName(p.short_name)}
          </text>
        </Link>
      ))}
    </Pitch>
  );
}
