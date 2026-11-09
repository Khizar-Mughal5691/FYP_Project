// Screen 4: one player's behaviour profile. What they do with the ball, how involved they are, and
// where on the pitch they have it, each against a typical player in the same position.
import { Link, useParams } from "react-router";
import { TrendingDown, TrendingUp } from "lucide-react";
import { usePlayer } from "../api/hooks";
import ActionMix, { styleNotes } from "../components/ActionMix";
import TeamBadge from "../components/TeamBadge";
import TouchMap from "../components/TouchMap";
import { BackLink, Card, Chip, ErrorPanel, SectionTitle, Skeleton, StatTile } from "../components/ui";
import { fixed, POSITION_NAMES } from "../lib/format";

export default function PlayerProfile() {
  const { playerId } = useParams();
  const player = usePlayer(playerId);

  if (player.isError) {
    return (
      <div className="flex flex-col gap-6">
        <BackLink to="/players">All players</BackLink>
        <ErrorPanel error={player.error} onRetry={player.error?.offline ? () => player.refetch() : undefined} />
      </div>
    );
  }
  if (player.isPending) return <Loading />;

  const p = player.data;
  const main = p.teams[0];
  const positionName = POSITION_NAMES[p.position] ?? "player";
  const typical = `Typical ${positionName}`;
  const notes = styleNotes(p.actions, positionName);
  const matches = p.teams.reduce((n, t) => n + t.matches, 0);
  const starts = p.teams.reduce((n, t) => n + t.starts, 0);
  const { decisions_per_match: perMatch, position_average: perMatchTypical } = p.involvement;

  return (
    <div className="flex flex-col gap-6">
      <BackLink to="/players">All players</BackLink>

      <header className="relative overflow-hidden rounded-3xl border border-white/8 bg-gradient-to-br from-pitch-800 via-pitch-850 to-pitch-900 p-6 sm:p-8">
        {main?.number != null && (
          <span aria-hidden className="pointer-events-none absolute -top-8 right-2 font-display text-[10rem] font-bold leading-none text-white/[0.05] sm:right-8 sm:text-[13rem]">
            {main.number}
          </span>
        )}
        <p className="relative text-xs font-semibold uppercase tracking-[0.18em] text-turf">Player profile</p>
        <h1 className="relative mt-2 font-display text-5xl font-bold uppercase leading-none tracking-wide text-balance">{p.short_name}</h1>
        {p.short_name !== p.name && <p className="relative mt-2 text-mist">{p.name}</p>}
        <div className="relative mt-5 flex flex-wrap items-center gap-2">
          {p.teams.map((t) => (
            <Link key={t.id} to={`/teams/${t.id}`}
                  className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 py-1 pl-1 pr-3 text-sm font-semibold transition hover:border-turf/40 hover:text-turf">
              <TeamBadge team={t} size="sm" /> {t.name}{t.number != null && <span className="tabular text-xs text-fog">#{t.number}</span>}
            </Link>
          ))}
          <Chip>{capitalise(positionName)}</Chip>
          {main?.role && <Chip>{main.role}</Chip>}
        </div>
      </header>

      <Card className="grid grid-cols-2 gap-6 p-5 sm:p-6 md:grid-cols-4">
        <StatTile label="Decisions per match" value={fixed(perMatch, 1)} hint={`${typical}: ${fixed(perMatchTypical, 1)}`} />
        <StatTile label="Compared with typical" value={`${fixed(perMatch / perMatchTypical, 1)}×`} hint="as involved on the ball" />
        <StatTile label="Matches" value={matches} hint={`${starts} as a starter`} />
        <StatTile label="Shirt number" value={main?.number ?? "–"} hint={main?.name} />
      </Card>

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
        <Card className="flex flex-col gap-5 p-5 sm:p-6">
          <SectionTitle hint={`Share of ${p.short_name}'s on-ball decisions. The tick marks a typical ${positionName}.`}>
            Action mix
          </SectionTitle>
          <ActionMix actions={p.actions} name={p.short_name} typical={typical} />
        </Card>

        <Card className="flex flex-col gap-4 p-5 sm:p-6">
          <SectionTitle>Style in words</SectionTitle>
          {notes.length ? (
            <ul className="flex flex-col gap-3">
              {notes.map((n) => (
                <li key={n.key} className="flex items-start gap-3 text-sm leading-relaxed">
                  {n.more
                    ? <TrendingUp className="mt-0.5 size-4 shrink-0 text-turf" aria-label="More than typical" />
                    : <TrendingDown className="mt-0.5 size-4 shrink-0 text-fog" aria-label="Less than typical" />}
                  <span>{n.text}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-mist">Close to a typical {positionName} in every action.</p>
          )}
          <p className="border-t border-white/6 pt-4 text-sm leading-relaxed text-fog">
            In a simulation, the action model reads these shares, so {p.short_name} chooses passes, carries,
            dribbles and shots the way they did in real matches.
          </p>
        </Card>
      </div>

      <Card className="flex flex-col gap-5 p-5 sm:p-6">
        <SectionTitle hint={`Share of ${p.short_name}'s decisions in each 20 by 20 yard zone, with ${main?.name ?? "the team"} attacking to the right. When the ball goes to a zone, the simulator picks who receives it from maps like this one.`}>
          Touch map
        </SectionTitle>
        <TouchMap map={p.touch_map} name={p.short_name} typical={typical} />
      </Card>

      <p className="text-xs text-fog">{p.credit}</p>
    </div>
  );
}

const capitalise = (word) => word.charAt(0).toUpperCase() + word.slice(1);

function Loading() {
  return (
    <div className="flex flex-col gap-6" aria-busy="true">
      <Skeleton className="h-5 w-24" />
      <Skeleton className="h-48 rounded-3xl" />
      <Skeleton className="h-28 rounded-2xl" />
      <div className="grid gap-6 lg:grid-cols-2">
        <Skeleton className="h-80 rounded-2xl" />
        <Skeleton className="h-80 rounded-2xl" />
      </div>
      <p className="sr-only" role="status">Loading the player</p>
    </div>
  );
}
