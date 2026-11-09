// Small building blocks shared by every page.
import { Link } from "react-router";
import { AlertTriangle, ArrowLeft, Loader2, RefreshCw, Search } from "lucide-react";
import { START_API_COMMAND } from "../api/client";

export function cx(...parts) {
  return parts.filter(Boolean).join(" ");
}

export function Card({ className, children, ...rest }) {
  return (
    <div className={cx("rounded-2xl border border-white/8 bg-pitch-850/80 shadow-[0_1px_0_0_rgb(255_255_255/0.04)_inset] backdrop-blur", className)} {...rest}>
      {children}
    </div>
  );
}

export function PageHeader({ eyebrow, title, description, actions }) {
  return (
    <header className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
      <div className="max-w-3xl">
        {eyebrow && <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-turf">{eyebrow}</p>}
        <h1 className="font-display text-4xl font-bold uppercase leading-none tracking-wide text-balance md:text-5xl">{title}</h1>
        {description && <p className="mt-3 text-base leading-relaxed text-mist">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-3">{actions}</div>}
    </header>
  );
}

const BUTTON = {
  primary: "bg-turf text-pitch-950 hover:bg-[#5be096]",
  secondary: "border border-white/12 bg-white/4 text-chalk hover:bg-white/8",
  ghost: "text-mist hover:bg-white/6 hover:text-chalk",
};

export function Button({ to, variant = "primary", className, children, ...rest }) {
  const classes = cx(
    "inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition-colors",
    "disabled:cursor-not-allowed disabled:opacity-50",
    BUTTON[variant], className);
  return to
    ? <Link to={to} className={classes} {...rest}>{children}</Link>
    : <button type="button" className={classes} {...rest}>{children}</button>;
}

export function Chip({ tone = "neutral", children, className }) {
  const tones = {
    neutral: "border-white/10 bg-white/5 text-mist",
    turf: "border-turf/30 bg-turf/10 text-turf",
    gold: "border-gold/30 bg-gold/10 text-gold",
    alert: "border-alert/30 bg-alert/10 text-alert",
  };
  return (
    <span className={cx("inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold", tones[tone], className)}>
      {children}
    </span>
  );
}

export function StatTile({ label, value, hint, loading }) {
  return (
    <div className="flex min-w-0 flex-col gap-1">
      <span className="text-xs font-semibold uppercase tracking-[0.14em] text-fog">{label}</span>
      {loading
        ? <span className="h-9 w-20 animate-pulse rounded-lg bg-white/8" />
        : <span className="tabular font-display text-4xl font-bold leading-none">{value}</span>}
      {hint && <span className="text-sm text-mist">{hint}</span>}
    </div>
  );
}

export function Spinner({ label = "Loading" }) {
  return (
    <span role="status" className="inline-flex items-center gap-2 text-sm text-mist">
      <Loader2 className="size-4 animate-spin" aria-hidden /> {label}
    </span>
  );
}

export function Skeleton({ className }) {
  return <span aria-hidden className={cx("block animate-pulse rounded-lg bg-white/8", className)} />;
}

export function SectionTitle({ id, children, hint, actions }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div className="min-w-0">
        <h2 id={id} className="font-display text-2xl font-bold uppercase tracking-wide">{children}</h2>
        {hint && <p className="mt-1 text-sm leading-relaxed text-mist">{hint}</p>}
      </div>
      {actions}
    </div>
  );
}

// A row of buttons where exactly one is chosen, such as a league filter.
export function Toggle({ label, options, value, onChange, size = "md" }) {
  return (
    <div role="group" aria-label={label}
         className="inline-flex max-w-full flex-wrap gap-1 rounded-xl border border-white/8 bg-pitch-900/60 p-1">
      {options.map((o) => {
        const on = o.value === value;
        return (
          <button key={o.value} type="button" aria-pressed={on} onClick={() => onChange(o.value)}
                  className={cx("inline-flex items-center gap-1.5 rounded-lg font-semibold transition-colors",
                                size === "sm" ? "px-2.5 py-1 text-xs" : "px-3 py-1.5 text-sm",
                                on ? "bg-turf text-pitch-950" : "text-mist hover:bg-white/6 hover:text-chalk")}>
            {o.label}
            {o.count != null && (
              <span className={cx("tabular text-xs", on ? "text-pitch-950/70" : "text-fog")}>{o.count}</span>
            )}
          </button>
        );
      })}
    </div>
  );
}

export function SearchBox({ label, value, onChange, placeholder }) {
  return (
    <div className="relative w-full sm:max-w-xs">
      <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-fog" aria-hidden />
      <input type="search" aria-label={label} value={value} placeholder={placeholder}
             onChange={(e) => onChange(e.target.value)}
             className="w-full rounded-xl border border-white/10 bg-pitch-900/70 py-2.5 pl-9 pr-3 text-sm text-chalk placeholder:text-fog hover:border-white/20 focus:border-turf/60" />
    </div>
  );
}

export function BackLink({ to, children }) {
  return (
    <Link to={to} className="inline-flex items-center gap-1.5 text-sm font-semibold text-mist transition-colors hover:text-chalk">
      <ArrowLeft className="size-4" aria-hidden /> {children}
    </Link>
  );
}

export function ErrorPanel({ error, onRetry }) {
  return (
    <Card role="alert" className="border-alert/30 bg-alert/5 p-5">
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 size-5 shrink-0 text-alert" aria-hidden />
        <div className="min-w-0 flex-1">
          <p className="font-semibold">{error?.offline ? "Cannot reach the API" : "Something went wrong"}</p>
          <p className="mt-1 text-sm text-mist">{error?.message}</p>
          {error?.offline && (
            <p className="mt-3 text-sm text-mist">
              In the project folder, run <code className="rounded bg-black/40 px-1.5 py-0.5 font-mono text-xs text-chalk">{START_API_COMMAND}</code>
            </p>
          )}
          {onRetry && (
            <Button variant="secondary" className="mt-4" onClick={onRetry}>
              <RefreshCw className="size-4" aria-hidden /> Try again
            </Button>
          )}
        </div>
      </div>
    </Card>
  );
}
