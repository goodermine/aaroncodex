export function Textarea({ className = "", ...props }) {
  return (
    <textarea
      className={`min-h-24 w-full rounded-xl border border-border/40 bg-black/20 px-3 py-2 text-sm text-white outline-none placeholder:text-muted-foreground ${className}`}
      {...props}
    />
  );
}
