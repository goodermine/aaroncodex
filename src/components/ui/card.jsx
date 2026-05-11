export function Card({ className = "", children }) {
  return <div className={`rounded-2xl border border-border/40 bg-black/20 ${className}`}>{children}</div>;
}
