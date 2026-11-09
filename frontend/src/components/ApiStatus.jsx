import { useHealth } from "../api/hooks";
import { cx } from "./ui";

export default function ApiStatus({ className }) {
  const health = useHealth();
  const state = health.isPending ? "connecting" : health.isError ? "offline" : "online";
  const text = { connecting: "Connecting to API", offline: "API offline", online: "API online" }[state];
  const dot = { connecting: "bg-gold animate-pulse", offline: "bg-alert", online: "bg-turf" }[state];
  return (
    <span role="status" title={health.error?.message}
          className={cx("inline-flex items-center gap-2 rounded-full border border-white/10 bg-black/20 px-3 py-1.5 text-xs font-semibold text-mist", className)}>
      <span className={cx("size-2 rounded-full", dot)} aria-hidden />
      {text}
    </span>
  );
}
