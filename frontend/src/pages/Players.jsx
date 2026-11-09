// The player finder: search 1,993 players by name, league and position, most involved first.
// A player opens their profile (screen 4).
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { ChevronRight, SearchX } from "lucide-react";
import { usePlayers } from "../api/hooks";
import TeamBadge from "../components/TeamBadge";
import { Button, Card, cx, ErrorPanel, PageHeader, SearchBox, Skeleton, Spinner, Toggle } from "../components/ui";
import { count, fixed, LEAGUES } from "../lib/format";

const PAGE = 60;
const MAX = 200;   // the API's largest page
const POSITIONS = [
  { value: "all", label: "All" }, { value: "GK", label: "Goalkeepers" }, { value: "DEF", label: "Defenders" },
  { value: "MID", label: "Midfielders" }, { value: "FWD", label: "Forwards" },
];

// The value only after it has stopped changing for `delay` ms, so typing does not send a request
// for every letter.
function useSettled(value, delay = 300) {
  const [settled, setSettled] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setSettled(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return settled;
}

export default function Players() {
  const [params, setParams] = useSearchParams();
  const league = params.get("league") ?? "all";
  const position = params.get("position") ?? "all";
  const [text, setText] = useState(params.get("q") ?? "");
  const search = useSettled(text.trim());
  const [limit, setLimit] = useState(PAGE);
  useEffect(() => setLimit(PAGE), [league, position, search]);

  const update = (key, value) => setParams((p) => {
    const next = new URLSearchParams(p);
    if (value && value !== "all") next.set(key, value); else next.delete(key);
    return next;
  }, { replace: true });
  useEffect(() => update("q", search), [search]);   // eslint-disable-line react-hooks/exhaustive-deps

  const players = usePlayers({
    search, limit, league: league === "all" ? "" : league, position: position === "all" ? "" : position,
  });
  const data = players.data;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader eyebrow="Player Behavioural Modelling" title="Players"
        description="Every player with a behaviour profile, most involved on the ball first. Search by name, or narrow down by league and position." />

      <div className="flex flex-col gap-3">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <Toggle label="League" value={league} onChange={(v) => update("league", v)}
                  options={[{ value: "all", label: "All leagues" }, ...LEAGUES.map((l) => ({ value: l.id, label: l.name }))]} />
          <SearchBox label="Search players" placeholder="Search players, e.g. Messi" value={text} onChange={setText} />
        </div>
        <Toggle label="Position" size="sm" options={POSITIONS} value={position} onChange={(v) => update("position", v)} />
      </div>

      {players.isError ? (
        <ErrorPanel error={players.error} onRetry={() => players.refetch()} />
      ) : !data ? (
        <div className="flex flex-col gap-2" aria-busy="true">
          {Array.from({ length: 8 }, (_, i) => <Skeleton key={i} className="h-16 rounded-2xl" />)}
          <p className="sr-only" role="status">Loading players</p>
        </div>
      ) : data.count === 0 ? (
        <Card className="flex flex-col items-center gap-2 p-10 text-center">
          <SearchX className="size-8 text-fog" aria-hidden />
          <p className="font-semibold">No player matches{search ? ` "${search}"` : " these filters"}</p>
          <p className="text-sm text-mist">Try a surname, such as "Suárez", or choose all leagues.</p>
        </Card>
      ) : (
        <section aria-label="Players found" className={cx("flex flex-col gap-3 transition-opacity", players.isPlaceholderData && "opacity-60")}>
          <div className="flex items-center justify-between gap-3 text-sm text-mist">
            <p role="status">
              <span className="tabular font-semibold text-chalk">{count(data.count)}</span> {data.count === 1 ? "player" : "players"} found
              {data.count > data.results.length && <> · showing the first {count(data.results.length)}</>}
            </p>
            {players.isFetching && <Spinner label="Updating" />}
          </div>
          <div className="hidden grid-cols-[minmax(0,2.2fr)_minmax(0,1.6fr)_4.5rem_5rem_6.5rem_1rem] gap-4 px-4 text-xs font-semibold text-fog md:grid">
            <span>Player</span><span>Team</span><span>Position</span>
            <span className="text-right">Matches</span><span className="text-right">Decisions / match</span><span />
          </div>
          <ul className="flex flex-col gap-2">
            {data.results.map((p) => <PlayerRow key={p.player_id} player={p} />)}
          </ul>
          {data.count > data.results.length && (
            limit < MAX ? (
              <Button variant="secondary" className="self-center" disabled={players.isFetching}
                      onClick={() => setLimit((n) => Math.min(n + PAGE, MAX))}>
                Show more players
              </Button>
            ) : (
              <p className="text-center text-sm text-mist">Showing the {MAX} most involved. Search or filter to find others.</p>
            )
          )}
        </section>
      )}
    </div>
  );
}

function PlayerRow({ player: p }) {
  return (
    <li>
      <Link to={`/players/${p.player_id}`}
            className="group grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-2 rounded-2xl border border-white/8 bg-pitch-850/80 px-4 py-3 transition hover:border-turf/40 hover:bg-pitch-800 md:grid-cols-[minmax(0,2.2fr)_minmax(0,1.6fr)_4.5rem_5rem_6.5rem_1rem]">
        <span className="flex min-w-0 items-center gap-3">
          <span className="tabular grid size-9 shrink-0 place-items-center rounded-full bg-chart-home/15 text-xs font-semibold text-home">
            {p.number ?? "–"}
          </span>
          <span className="min-w-0">
            <span className="block truncate font-semibold group-hover:text-turf">{p.short_name}</span>
            {p.short_name !== p.name && <span className="block truncate text-xs text-fog">{p.name}</span>}
          </span>
        </span>
        <span className="flex min-w-0 items-center gap-2 text-sm text-mist max-md:col-start-1 max-md:row-start-2">
          <TeamBadge team={p.team} size="sm" /> <span className="truncate">{p.team.name}</span>
        </span>
        <span className="text-xs font-semibold text-mist max-md:col-start-2 max-md:row-start-1 max-md:text-right">{p.position}</span>
        <span className="tabular hidden text-right text-sm md:block">{p.matches}</span>
        <span className="tabular text-right text-sm max-md:col-start-2 max-md:row-start-2">
          {fixed(p.decisions_per_match, 1)}<span className="text-fog md:hidden"> / match</span>
        </span>
        <ChevronRight className="hidden size-4 text-fog transition group-hover:translate-x-0.5 group-hover:text-turf md:block" aria-hidden />
      </Link>
    </li>
  );
}
