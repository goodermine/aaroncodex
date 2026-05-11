export function Input({ className = "", ...props }) {
  return (
    <input
      className={`w-full rounded-xl border border-border/40 bg-black/20 px-3 py-2 text-sm text-white outline-none placeholder:text-muted-foreground ${className}`}
      {...props}
    />
  );
}
