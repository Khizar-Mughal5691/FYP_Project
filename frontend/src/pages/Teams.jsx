// Screen 2: every team, filtered by league and name. A team opens its profile.
import { useState } from "react";
import { Link, useSearchParams } from "react-router";
import { motion, useReducedMotion } from "motion/react";
import { ChevronRight, SearchX } from "lucide-react";
import { useTeams } from "../api/hooks";
import TeamBadge from "../components/TeamBadge";
import { Card, ErrorPanel, PageHeader, SearchBox, Skeleton, Toggle } from "../components/ui";
import { LEAGUES, plain } from "../lib/format";

export default function Teams() {
  const teams = useTeams();
  const [params, setParams] = useSearchParams();
  const league = params.get("league") ?? "all";
  const [text, setText] = useState(params.get("q") ?? "");

  const update = (key, value) => setParams((p) => {
    const next = new URLSearchParams(p);
    if (value && value !== "all") next.set(key, value); else next.delete(key);
    return next;
  }, { replace: true });

  const all = teams.data ?? [];
  const wanted = plain(text);
  const matching = all.filter((t) => !wanted || plain(t.name).includes(wanted));
  const shown = matching.filter((t) => league === "all" || t.league === league);
  const options = [
    { value: "all", label: "All", count: matching.length },
    ...LEAGUES.map((l) => ({ value: l.id, label: l.name, count: matching.filter((t) => t.league === l.id).length })),
  ];
  const groups = LEAGUES.map((l) => ({ ...l, teams: shown.filter((t) => t.league === l.id) })).filter((g) => g.teams.length);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader eyebrow="Player Dataset Processing" title="Teams"
        description="All 80 teams of the 2015/16 Premier League, La Liga, Serie A and Ligue 1. Each has a profile learned from its matches: open one to see how it plays." />

      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <Toggle label="League" options={options} value={league} onChange={(v) => update("league", v)} />
        <SearchBox label="Search teams" placeholder="Search teams" value={text}
                   onChange={(v) => { setText(v); update("q", v.trim()); }} />
      </div>

      {teams.isError ? (
        <ErrorPanel error={teams.error} onRetry={() => teams.refetch()} />
      ) : teams.isPending ? (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3" aria-busy="true">
          {Array.from({ length: 9 }, (_, i) => <Skeleton key={i} className="h-[4.75rem] rounded-2xl" />)}
        </div>
      ) : shown.length === 0 ? (
        <Card className="flex flex-col items-center gap-2 p-10 text-center">
          <SearchX className="size-8 text-fog" aria-hidden />
          <p className="font-semibold">No team matches "{text}"</p>
          <p className="text-sm text-mist">Try part of the name, such as "Real" or "United".</p>
        </Card>
      ) : (
        <div className="flex flex-col gap-8">
          {groups.map((g) => (
            <section key={g.id} aria-labelledby={`league-${g.id}`}>
              <h2 id={`league-${g.id}`} className="mb-3 flex items-baseline gap-2 font-display text-xl font-bold uppercase tracking-wide">
                {g.name} <span className="tabular font-sans text-sm font-semibold text-fog">{g.teams.length}</span>
              </h2>
              <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {g.teams.map((t, i) => <TeamCard key={t.id} team={t} index={i} />)}
              </ul>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}

function TeamCard({ team, index }) {
  const reduce = useReducedMotion();
  return (
    <motion.li initial={reduce ? false : { opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
               transition={{ duration: 0.25, delay: Math.min(index, 12) * 0.025 }}>
      <Link to={`/teams/${team.id}`}
            className="group flex items-center gap-3 rounded-2xl border border-white/8 bg-pitch-850/80 p-4 transition hover:-translate-y-0.5 hover:border-turf/40 hover:bg-pitch-800">
        <TeamBadge team={team} />
        <span className="min-w-0 flex-1">
          <span className="block truncate font-semibold">{team.name}</span>
          <span className="block text-xs text-fog">{team.league_name}</span>
        </span>
        <ChevronRight className="size-4 shrink-0 text-fog transition group-hover:translate-x-0.5 group-hover:text-turf" aria-hidden />
      </Link>
    </motion.li>
  );
}
