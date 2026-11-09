import { ArrowRight, Database, Dices, Sparkles, UserRoundSearch } from "lucide-react";
import { useHealth } from "../api/hooks";
import HeroPitch from "../components/HeroPitch";
import { Button, Card, Chip, ErrorPanel, StatTile } from "../components/ui";

// The steps of the method, in order: each one feeds the next.
const STEPS = [
  { icon: Database, title: "Real match data", text: "1,517 matches of the 2015/16 season, broken into 2.8 million on-ball decisions." },
  { icon: UserRoundSearch, title: "Team and player profiles", text: "How each team keeps the ball and presses, and how each player behaves on it." },
  { icon: Dices, title: "Event-driven simulation", text: "A match is played one decision at a time, about 1,870 of them, by learned models." },
  { icon: Sparkles, title: "Probabilities and insight", text: "Hundreds of simulations of the same fixture give its likely outcomes and scorers." },
];

const fmt = (n) => (typeof n === "number" ? n.toLocaleString("en-US") : n);

export default function Home() {
  const health = useHealth();
  const data = health.data;
  return (
    <div className="flex flex-col gap-12">
      <section className="grid items-center gap-10 pt-4 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)]">
        <div>
          <Chip tone="turf">Final Year Project · The University of Lahore</Chip>
          <h1 className="mt-5 font-display text-5xl font-bold uppercase leading-[0.95] tracking-wide text-balance sm:text-6xl xl:text-7xl">
            Simulate football,<br /><span className="text-turf">one decision</span><br />at a time.
          </h1>
          <p className="mt-5 max-w-xl text-lg leading-relaxed text-mist">
            Meta-Fut A.I learns how the teams and players of four top leagues really play, then simulates
            any match between them hundreds of times to show what is likely to happen, and why.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Button to="/simulate">Simulate a match <ArrowRight className="size-4" aria-hidden /></Button>
            <Button to="/teams" variant="secondary">Explore teams</Button>
          </div>
        </div>
        <HeroPitch />
      </section>

      <section aria-label="What the simulator knows">
        {health.isError ? (
          <ErrorPanel error={health.error} onRetry={() => health.refetch()} />
        ) : (
          <Card className="grid grid-cols-2 gap-6 p-6 md:grid-cols-4">
            <StatTile label="Teams" value={fmt(data?.teams)} loading={health.isPending} hint="With their own profiles" />
            <StatTile label="Players" value={fmt(data?.players)} loading={health.isPending} hint="Each with a behaviour profile" />
            <StatTile label="Leagues" value={data?.leagues?.length} loading={health.isPending} hint="2015/16 season" />
            <div className="flex min-w-0 flex-col gap-2">
              <span className="text-xs font-semibold uppercase tracking-[0.14em] text-fog">Competitions</span>
              <div className="flex flex-wrap gap-1.5">
                {health.isPending
                  ? <span className="h-7 w-40 animate-pulse rounded-full bg-white/8" />
                  : data?.leagues?.map((l) => <Chip key={l.id}>{l.name}</Chip>)}
              </div>
            </div>
          </Card>
        )}
      </section>

      <section aria-labelledby="how-title">
        <h2 id="how-title" className="font-display text-3xl font-bold uppercase tracking-wide">How it works</h2>
        <ol className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {STEPS.map(({ icon: Icon, title, text }, i) => (
            <li key={title}>
              <Card className="flex h-full flex-col gap-3 p-5">
                <div className="flex items-center justify-between">
                  <span className="grid size-10 place-items-center rounded-xl bg-turf/10 text-turf"><Icon className="size-5" aria-hidden /></span>
                  <span className="font-display text-3xl font-bold text-white/15">{i + 1}</span>
                </div>
                <h3 className="font-semibold">{title}</h3>
                <p className="text-sm leading-relaxed text-mist">{text}</p>
              </Card>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
