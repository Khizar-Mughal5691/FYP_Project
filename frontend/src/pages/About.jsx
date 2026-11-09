import { ExternalLink } from "lucide-react";
import { Card, Chip, PageHeader } from "../components/ui";

// What each proposal module looks like today. Keep this honest: it is shown to the panel.
const MODULES = [
  ["Player Dataset Processing", "Built"],
  ["Player Behavioural Modelling", "Built"],
  ["Context-Aware Decision Engine", "Built"],
  ["Event-Driven Simulation Engine", "Built"],
  ["Scenario Simulation & Rollout", "Partly built"],
  ["Outcome Analysis", "Partly built"],
  ["Visualization & Interface", "In progress"],
  ["Tactical / Managerial Input", "Next"],
];
const TONE = { Built: "turf", "Partly built": "gold", "In progress": "gold", Next: "neutral" };

const CHECKS = [
  ["Pass model", "Log loss 0.354 against a limit of 0.36; predicted and real completion differ by at most 0.4 points on average."],
  ["Simulated league", "1,000 simulated matches against 1,213 real ones: 2.72 goals per match (real 2.50), 968 passes (real 974), 76.8% pass completion (real 77.1%)."],
  ["Unseen matches", "303 later matches simulated 100 times each. The forecast beats fixed home/draw/away rates (score 0.217 against 0.228) but is behind the Dixon-Coles model (0.201) and bookmakers (0.195). Team possession correlates 0.83 with reality."],
];

export default function About() {
  return (
    <div className="flex flex-col gap-8">
      <PageHeader eyebrow="About" title="Meta-Fut A.I"
        description="A context-aware football simulation system. It models how real teams and players behave, plays matches out decision by decision, and runs each fixture many times to estimate what is likely to happen." />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
        <Card className="p-6">
          <h2 className="font-display text-2xl font-bold uppercase tracking-wide">The problem</h2>
          <p className="mt-3 leading-relaxed text-mist">
            Most football analysis tools describe matches that have already been played. Coaches and analysts
            have few ways to test a decision, such as a lineup or a style of play, before a match. Meta-Fut A.I
            learns behaviour from real event data and simulates matches that have not happened yet.
          </p>
          <h2 className="mt-6 font-display text-2xl font-bold uppercase tracking-wide">The modules</h2>
          <ul className="mt-3 divide-y divide-white/6">
            {MODULES.map(([name, status]) => (
              <li key={name} className="flex items-center justify-between gap-4 py-2.5 text-sm">
                <span>{name}</span><Chip tone={TONE[status]}>{status}</Chip>
              </li>
            ))}
          </ul>
        </Card>

        <div className="flex flex-col gap-6">
          <Card className="p-6">
            <h2 className="font-display text-2xl font-bold uppercase tracking-wide">The team</h2>
            <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
              <dt className="text-fog">Group leader</dt><dd>Faizan Ahmad</dd>
              <dt className="text-fog">Member</dt><dd>Khizar-ul-Islam</dd>
              <dt className="text-fog">Supervisor</dt><dd>Sir Ahmad Zia</dd>
              <dt className="text-fog">Department</dt><dd>Computer Science & IT, The University of Lahore</dd>
            </dl>
          </Card>
          <Card className="p-6">
            <h2 className="font-display text-2xl font-bold uppercase tracking-wide">Built with</h2>
            <div className="mt-3 flex flex-wrap gap-2">
              {["Python", "NumPy", "pandas", "scikit-learn", "Django REST Framework", "React", "Vite", "Tailwind CSS"].map((t) => <Chip key={t}>{t}</Chip>)}
            </div>
          </Card>
        </div>
      </div>

      <Card className="p-6">
        <h2 className="font-display text-2xl font-bold uppercase tracking-wide">How it was tested</h2>
        <ul className="mt-4 grid gap-4 md:grid-cols-3">
          {CHECKS.map(([title, text]) => (
            <li key={title}>
              <h3 className="font-semibold text-turf">{title}</h3>
              <p className="mt-1 text-sm leading-relaxed text-mist">{text}</p>
            </li>
          ))}
        </ul>
      </Card>

      <Card className="p-6">
        <h2 className="font-display text-2xl font-bold uppercase tracking-wide">Data</h2>
        <p className="mt-3 max-w-3xl text-sm leading-relaxed text-mist">
          Match events come from StatsBomb open data for the 2015/16 Premier League, La Liga, Serie A and Ligue 1,
          used for non-commercial research. Bookmaker odds from football-data.co.uk are used only to benchmark the
          forecasts.
        </p>
        <a href="https://github.com/statsbomb/open-data" target="_blank" rel="noreferrer"
           className="mt-3 inline-flex items-center gap-1.5 text-sm font-semibold text-turf hover:underline">
          StatsBomb open data <ExternalLink className="size-3.5" aria-hidden />
        </a>
      </Card>
    </div>
  );
}
