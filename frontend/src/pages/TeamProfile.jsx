// Screen 3: one team's profile. Eight numbers ranked against all 80 teams, the usual eleven on a
// pitch, and the squad.
import { useState } from "react";
import { Link, useParams } from "react-router";
import { ArrowDown, ArrowUp, Play } from "lucide-react";
import { useTeam } from "../api/hooks";
import LineupPitch from "../components/LineupPitch";
import ProfileMeters, { metricTitle } from "../components/ProfileMeters";
import TeamBadge from "../components/TeamBadge";
import { BackLink, Button, Card, Chip, ErrorPanel, SectionTitle, Skeleton, cx } from "../components/ui";
import { count, ordinal, POSITION_NAMES } from "../lib/format";

export default function TeamProfile() {
  const { teamId } = useParams();
  const team = useTeam(teamId);

  if (team.isError) {
    return (
      <div className="flex flex-col gap-6">
        <BackLink to="/teams">All teams</BackLink>
        <ErrorPanel error={team.error} onRetry={team.error?.offline ? () => team.refetch() : undefined} />
      </div>
    );
  }
  if (team.isPending) return <Loading />;

  const t = team.data;
  const ranked = [...t.profile].sort((a, b) => a.rank - b.rank);
  return (
    <div className="flex flex-col gap-6">
      <BackLink to="/teams">All teams</BackLink>

      <header className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-5">
          <TeamBadge team={t} size="lg" />
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-turf">Team profile</p>
            <h1 className="mt-1 font-display text-4xl font-bold uppercase leading-none tracking-wide text-balance md:text-5xl">{t.name}</h1>
            <div className="mt-3 flex flex-wrap gap-2">
              <Chip>{t.league_name}</Chip>
              {t.formation && <Chip>Usually {t.formation}</Chip>}
              <Chip>{count(t.squad.length)} players used</Chip>
            </div>
          </div>
        </div>
        <Button to={`/simulate?home=${t.id}`} className="self-start md:self-center">
          <Play className="size-4" aria-hidden /> Simulate a match
        </Button>
      </header>

      <Card className="grid gap-6 p-5 sm:grid-cols-2 sm:p-6">
        <Standouts title="Best ranks" icon={ArrowUp} tone="text-turf" items={ranked.slice(0, 3)} />
        <Standouts title="Lowest ranks" icon={ArrowDown} tone="text-fog" items={ranked.slice(-2).reverse()} />
      </Card>

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)]">
        <Card className="flex flex-col gap-6 p-5 sm:p-6">
          <SectionTitle hint="Where the team ranks among all 80 teams. A full bar is the best of the four leagues, whether that means the highest or the lowest number.">
            Style profile
          </SectionTitle>
          <ProfileMeters profile={t.profile} />
        </Card>

        <Card className="flex flex-col gap-5 p-5 sm:p-6">
          <SectionTitle hint="The goalkeeper and ten outfield players with the most starts, each placed by their usual role. Select a player to open their profile.">
            Usual eleven
          </SectionTitle>
          <LineupPitch players={t.usual_xi} title={`${t.name} usual eleven`} className="w-full" />
          <ol className="grid gap-x-6 gap-y-2.5 text-sm sm:grid-cols-2">
            {t.usual_xi.map((p) => (
              <li key={p.player_id} className="flex items-start gap-3">
                <span className="tabular w-6 shrink-0 pt-0.5 text-right text-xs font-semibold text-fog">{p.number ?? "–"}</span>
                <span className="min-w-0">
                  <Link to={`/players/${p.player_id}`} className="block truncate font-semibold hover:text-turf">{p.short_name}</Link>
                  <span className="block text-xs text-fog">{p.role ?? POSITION_NAMES[p.position]}</span>
                </span>
              </li>
            ))}
          </ol>
        </Card>
      </div>

      <Card className="flex flex-col gap-4 p-5 sm:p-6">
        <SectionTitle hint="Everyone who played for the team in the matches the profiles were learned from. Select a column to sort.">
          Squad
        </SectionTitle>
        <SquadTable squad={t.squad} />
      </Card>

      <p className="text-xs text-fog">{t.credit}</p>
    </div>
  );
}

function Standouts({ title, icon: Icon, tone, items }) {
  return (
    <div>
      <h2 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-fog">
        <Icon className={cx("size-4", tone)} aria-hidden /> {title}
      </h2>
      <ul className="mt-3 flex flex-col gap-2">
        {items.map((n) => (
          <li key={n.key} className="flex items-baseline gap-3">
            <span className="tabular w-12 shrink-0 font-display text-2xl font-bold leading-none">{ordinal(n.rank)}</span>
            <span className="text-sm text-mist">{metricTitle(n.key)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

const COLUMNS = [
  { key: "player", label: "Player", sort: (p) => p.short_name },
  { key: "role", label: "Role", sort: (p) => p.role ?? "", className: "hidden md:table-cell" },
  { key: "starts", label: "Starts", sort: (p) => p.starts, numeric: true },
  { key: "matches", label: "Matches", sort: (p) => p.matches, numeric: true, className: "hidden sm:table-cell" },
  { key: "decisions", label: "Decisions", sort: (p) => p.decisions, numeric: true },
];

function SquadTable({ squad }) {
  const [order, setOrder] = useState({ key: "starts", descending: true });
  const column = COLUMNS.find((c) => c.key === order.key);
  const sorted = [...squad].sort((a, b) => {
    const x = column.sort(a), y = column.sort(b);
    const diff = typeof x === "string" ? x.localeCompare(y) : x - y;
    return order.descending ? -diff : diff;
  });
  const most = Math.max(...squad.map((p) => p.starts), 1);
  const choose = (c) => setOrder((o) => (o.key === c.key ? { key: c.key, descending: !o.descending } : { key: c.key, descending: c.numeric }));

  return (
    <div className="-mx-2 overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-white/8 text-xs text-fog">
            <th scope="col" className="w-10 px-2 py-2 text-right font-semibold">#</th>
            {COLUMNS.map((c) => (
              <th key={c.key} scope="col" className={cx("px-2 py-2 font-semibold", c.numeric ? "text-right" : "text-left", c.className)}
                  aria-sort={order.key === c.key ? (order.descending ? "descending" : "ascending") : undefined}>
                <button type="button" onClick={() => choose(c)} className="inline-flex items-center gap-1 hover:text-chalk">
                  {c.label}
                  {order.key === c.key && (order.descending ? <ArrowDown className="size-3" aria-hidden /> : <ArrowUp className="size-3" aria-hidden />)}
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {sorted.map((p) => (
            <tr key={p.player_id} className="hover:bg-white/[0.03]">
              <td className="tabular px-2 py-2 text-right text-xs text-fog">{p.number ?? "–"}</td>
              <td className="px-2 py-2">
                <Link to={`/players/${p.player_id}`} className="font-semibold hover:text-turf">{p.short_name}</Link>
                <span className="ml-2 inline-block rounded bg-white/6 px-1.5 py-0.5 align-middle text-[0.65rem] font-semibold text-mist">{p.position}</span>
              </td>
              <td className="hidden px-2 py-2 text-mist md:table-cell">{p.role ?? "Substitute only"}</td>
              <td className="px-2 py-2">
                <div className="flex items-center justify-end gap-2">
                  <span className="hidden h-1.5 w-16 rounded-full bg-chart/15 sm:block" aria-hidden>
                    <span className="block h-full rounded-full bg-chart" style={{ width: `${(p.starts / most) * 100}%` }} />
                  </span>
                  <span className="tabular w-6 text-right">{p.starts}</span>
                </div>
              </td>
              <td className="tabular hidden px-2 py-2 text-right sm:table-cell">{p.matches}</td>
              <td className="tabular px-2 py-2 text-right">{count(p.decisions)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Loading() {
  return (
    <div className="flex flex-col gap-6" aria-busy="true">
      <Skeleton className="h-5 w-24" />
      <div className="flex items-center gap-5">
        <Skeleton className="size-20 rounded-2xl" />
        <div className="flex flex-col gap-3"><Skeleton className="h-10 w-64" /><Skeleton className="h-6 w-48" /></div>
      </div>
      <Skeleton className="h-32 rounded-2xl" />
      <div className="grid gap-6 lg:grid-cols-2">
        <Skeleton className="h-[32rem] rounded-2xl" />
        <Skeleton className="h-[32rem] rounded-2xl" />
      </div>
      <p className="sr-only" role="status">Loading the team</p>
    </div>
  );
}
