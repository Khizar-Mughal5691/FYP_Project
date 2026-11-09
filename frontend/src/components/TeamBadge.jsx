// A shield with the team's letters. The colour comes from the team's id, so a team looks the same
// on every screen. These are not the real club crests.
import { monogram, teamHue } from "../lib/teams";
import { cx } from "./ui";

const SIZES = { sm: "size-8 text-[0.62rem]", md: "size-11 text-xs", lg: "size-20 text-xl" };

export default function TeamBadge({ team, size = "md", className }) {
  const hue = teamHue(team.id);
  return (
    <span aria-hidden className={cx("relative inline-grid shrink-0 place-items-center", SIZES[size], className)}>
      <svg viewBox="0 0 40 46" className="absolute inset-0 size-full">
        <path d="M20 1.5 L38 7.5 V22 C38 33.5 30.5 40.5 20 44.5 C9.5 40.5 2 33.5 2 22 V7.5 Z"
              fill={`hsl(${hue} 40% 27%)`} stroke={`hsl(${hue} 55% 60%)`} strokeWidth="1.6" />
        <path d="M20 4.5 L35 9.5 V22 C35 31.5 28.8 37.5 20 41 Z" fill="white" fillOpacity="0.07" />
      </svg>
      <span className="relative -mt-0.5 font-display font-bold tracking-wide text-chalk">{monogram(team.name)}</span>
    </span>
  );
}
