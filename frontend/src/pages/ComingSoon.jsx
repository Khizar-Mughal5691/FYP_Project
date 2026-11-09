// A screen from a later batch. It already has its place in the menu and says what it will do.
import { Check, Hammer } from "lucide-react";
import Pitch from "../components/Pitch";
import { Card, Chip, PageHeader } from "../components/ui";

export default function ComingSoon({ screen }) {
  const Icon = screen.icon;
  return (
    <div className="flex flex-col gap-8">
      <PageHeader eyebrow={screen.module} title={screen.title} description={screen.description} />
      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
        <Card className="flex flex-col gap-4 p-6">
          <div className="flex items-center gap-3">
            <span className="grid size-11 place-items-center rounded-xl bg-gold/10 text-gold"><Hammer className="size-5" aria-hidden /></span>
            <div>
              <p className="font-semibold">Being built</p>
              <Chip tone="gold" className="mt-1">Arrives in batch {screen.batch}</Chip>
            </div>
          </div>
          {screen.features && (
            <ul className="flex flex-col gap-2 text-sm">
              {screen.features.map((f) => (
                <li key={f} className="flex items-start gap-2 text-mist">
                  <Check className="mt-0.5 size-4 shrink-0 text-turf" aria-hidden /> {f}
                </li>
              ))}
            </ul>
          )}
        </Card>
        <div className="relative">
          <Pitch className="w-full opacity-40" />
          <div className="absolute inset-0 grid place-items-center">
            <Icon className="size-16 text-turf/70" aria-hidden />
          </div>
        </div>
      </div>
    </div>
  );
}
