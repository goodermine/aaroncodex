export function AlertDialog({ children }) {
  return <>{children}</>;
}

export function AlertDialogTrigger({ children }) {
  return <>{children}</>;
}

export function AlertDialogContent({ className = "", children }) {
  return <div className={`rounded-2xl border border-border/40 bg-black/30 p-4 ${className}`}>{children}</div>;
}

export function AlertDialogHeader({ children }) {
  return <div className="mb-3">{children}</div>;
}

export function AlertDialogTitle({ className = "", children }) {
  return <h3 className={`font-semibold ${className}`}>{children}</h3>;
}

export function AlertDialogDescription({ className = "", children }) {
  return <div className={className}>{children}</div>;
}

export function AlertDialogFooter({ className = "", children }) {
  return <div className={`mt-4 flex gap-2 ${className}`}>{children}</div>;
}

export function AlertDialogCancel({ className = "", children, ...props }) {
  return (
    <button type="button" className={`rounded-xl border border-border/40 px-3 py-2 ${className}`} {...props}>
      {children}
    </button>
  );
}

export function AlertDialogAction({ className = "", children, ...props }) {
  return (
    <button type="button" className={`rounded-xl bg-red-500/80 px-3 py-2 text-white ${className}`} {...props}>
      {children}
    </button>
  );
}
