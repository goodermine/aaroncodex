export function Badge({ className = "", children }) {
  return <span className={`inline-flex items-center rounded-full border px-2 py-1 text-xs ${className}`}>{children}</span>;
}
