// A football pitch in StatsBomb units: 120 by 80 yards, x from one goal to the other. Anything
// passed as children is drawn in the same units, so the API's coordinates can be used as they are.
// `underlay` is drawn below the pitch lines (for example a heatmap), `children` above them.

const LINE = { fill: "none", stroke: "currentColor", strokeWidth: 0.5 };

export default function Pitch({ children, underlay, className, stripes = true, title, role }) {
  return (
    <svg viewBox="-4 -4 128 88" className={className} role={role ?? (title ? "img" : undefined)}
         aria-label={title} aria-hidden={title ? undefined : true}>
      <rect x="0" y="0" width="120" height="80" rx="1" className="fill-pitch-800" />
      {stripes && Array.from({ length: 12 }, (_, i) => (
        <rect key={i} x={i * 10} y="0" width="10" height="80" className={i % 2 ? "fill-white/[0.025]" : "fill-transparent"} />
      ))}
      {underlay}
      <g className="pointer-events-none text-white/25">
        <rect x="0" y="0" width="120" height="80" {...LINE} />
        <line x1="60" y1="0" x2="60" y2="80" {...LINE} />
        <circle cx="60" cy="40" r="10" {...LINE} />
        <circle cx="60" cy="40" r="0.6" fill="currentColor" />
        {[0, 1].map((side) => {
          const flip = (x) => (side ? 120 - x : x);
          const box = (depth, half) => {
            const x0 = Math.min(flip(0), flip(depth));
            return <rect x={x0} y={40 - half} width={depth} height={half * 2} {...LINE} />;
          };
          return (
            <g key={side}>
              {box(18, 22)}
              {box(6, 10)}
              <circle cx={flip(12)} cy="40" r="0.6" fill="currentColor" />
              {/* The arc is 10 yards from the penalty spot; it meets the box line 8 yards either side. */}
              <path d={side ? "M 102 32 A 10 10 0 0 0 102 48" : "M 18 32 A 10 10 0 0 1 18 48"} {...LINE} />
              <rect x={side ? 120 : -2} y="36" width="2" height="8" {...LINE} />
            </g>
          );
        })}
      </g>
      {children}
    </svg>
  );
}
