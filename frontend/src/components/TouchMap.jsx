// Where a player has the ball: the share of their decisions in each 20 by 20 yard zone, drawn as a
// heatmap on a pitch with the player's team attacking to the right. One colour, brighter for more;
// the player and a typical player in the same position share one scale, so they can be compared.
import { useState } from "react";
import { pct } from "../lib/format";
import Pitch from "./Pitch";
import { Button, Toggle } from "./ui";

const COLUMNS = ["Own box", "Own third", "Own half", "Opponent half", "Final third", "Opponent box"];
const ROWS = ["Left flank", "Left centre", "Right centre", "Right flank"];
const LABEL_FROM = 0.05;   // zones with at least this share show their number on the pitch

export default function TouchMap({ map, name, typical }) {
  const [view, setView] = useState("player");
  const [asTable, setAsTable] = useState(false);
  const [zone, setZone] = useState(null);
  const { columns, rows } = map;
  const values = view === "player" ? map.values : map.position_average;
  const max = Math.max(...map.values, ...map.position_average) || 1;
  const strength = (v) => 0.05 + 0.85 * (v / max);
  const zoneName = (i) => `${COLUMNS[i % columns] ?? `Column ${i % columns}`}, ${(ROWS[Math.floor(i / columns)] ?? "").toLowerCase()}`;
  const shown = view === "player" ? name : `a ${typical.toLowerCase()}`;
  const busiest = values.map((_, i) => i).sort((a, b) => values[b] - values[a]).slice(0, 3);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Toggle label="Show the touch map of" size="sm" value={view} onChange={setView}
                options={[{ value: "player", label: name }, { value: "typical", label: typical }]} />
        <Button variant="ghost" className="px-2 py-1 text-xs" aria-pressed={asTable} onClick={() => setAsTable((t) => !t)}>
          {asTable ? "Show on the pitch" : "Show as a table"}
        </Button>
      </div>

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_15rem]">
        <div className="min-w-0">
          {asTable
            ? <ZoneTable values={values} columns={columns} rows={rows} caption={`Share of ${shown}'s decisions in each zone`} />
            : <HeatPitch map={map} values={values} strength={strength} zone={zone} setZone={setZone}
                         zoneName={zoneName} title={`Touch map of ${shown}`} />}
        </div>

        <aside className="flex flex-col gap-5 text-sm">
          <p aria-live="polite" className="min-h-10 leading-relaxed text-mist">
            {zone == null
              ? "Point at or tap a zone for its numbers."
              : <><span className="font-semibold text-chalk">{zoneName(zone)}</span>: {pct(map.values[zone])} for {name}, {pct(map.position_average[zone])} for {typical.toLowerCase()}</>}
          </p>
          {!asTable && (
            <div aria-hidden>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-fog">Share of decisions</p>
              <div className="mt-2 flex items-center gap-2 text-xs text-fog">
                <span>0%</span>
                <span className="h-2 flex-1 rounded-full bg-pitch-800"
                      style={{ backgroundImage: "linear-gradient(to right, rgb(60 207 126 / 0.05), rgb(60 207 126 / 0.9))" }} />
                <span className="tabular">{pct(max, 0)}</span>
              </div>
            </div>
          )}
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-fog">Busiest zones</p>
            <ol className="mt-2 flex flex-col gap-1.5">
              {busiest.map((i) => (
                <li key={i} className="flex items-baseline justify-between gap-3">
                  <span className="text-mist">{zoneName(i)}</span>
                  <span className="tabular font-semibold">{pct(values[i])}</span>
                </li>
              ))}
            </ol>
          </div>
        </aside>
      </div>
    </div>
  );
}

function HeatPitch({ map, values, strength, zone, setZone, zoneName, title }) {
  const { columns } = map;
  const [w, h] = map.zone_size_yards;
  const box = (i) => ({ x: (i % columns) * w + 0.4, y: Math.floor(i / columns) * h + 0.4, width: w - 0.8, height: h - 0.8 });
  return (
    <Pitch className="w-full" stripes={false} role="group" title={title}
           underlay={values.map((v, i) => (
             <rect key={i} {...box(i)} rx="1.2" strokeWidth="0.6" fillOpacity={strength(v)}
                   className="cursor-crosshair fill-turf outline-none focus-visible:stroke-gold"
                   tabIndex={0} aria-label={`${zoneName(i)}: ${pct(v)}`}
                   onMouseEnter={() => setZone(i)} onFocus={() => setZone(i)}
                   onMouseLeave={() => setZone(null)} onBlur={() => setZone(null)} />
           ))}>
      {values.map((v, i) => v >= LABEL_FROM && (
        <text key={i} x={(i % columns) * w + w / 2} y={Math.floor(i / columns) * h + h / 2} dy="0.35em" textAnchor="middle"
              className={`pointer-events-none text-[3.6px] font-semibold ${strength(v) > 0.55 ? "fill-pitch-950" : "fill-chalk"}`}>
          {pct(v, 0)}
        </text>
      ))}
      {zone != null && <rect {...box(zone)} rx="1.2" strokeWidth="0.6" className="pointer-events-none fill-none stroke-gold" />}
      <text x="60" y="83.2" textAnchor="middle" className="fill-fog text-[2.6px] font-semibold uppercase tracking-[0.3em]">
        Attacking direction →
      </text>
    </Pitch>
  );
}

function ZoneTable({ values, columns, rows, caption }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[34rem] text-sm">
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr className="text-xs text-fog">
            <th scope="col" className="py-2 text-left font-semibold">Zone</th>
            {COLUMNS.slice(0, columns).map((c) => <th key={c} scope="col" className="px-2 py-2 text-right font-semibold">{c}</th>)}
          </tr>
        </thead>
        <tbody className="divide-y divide-white/6">
          {ROWS.slice(0, rows).map((r, ri) => (
            <tr key={r}>
              <th scope="row" className="py-2 text-left font-normal text-mist">{r}</th>
              {values.slice(ri * columns, ri * columns + columns).map((v, ci) => (
                <td key={ci} className="tabular px-2 py-2 text-right">{pct(v)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
