export function Dialog({ open = false, children }) {
  return open ? <div>{children}</div> : null;
}

export function DialogContent({ className = "", children }) {
  return <div className={`fixed inset-0 z-50 m-auto h-fit max-w-lg rounded-2xl border border-border/40 bg-[#08111f] p-6 ${className}`}>{children}</div>;
}

export function DialogHeader({ children }) {
  return <div className="mb-4">{children}</div>;
}

export function DialogTitle({ className = "", children }) {
  return <h2 className={`font-semibold ${className}`}>{children}</h2>;
}

export function DialogDescription({ className = "", children }) {
  return <p className={className}>{children}</p>;
}

export function DialogFooter({ className = "", children }) {
  return <div className={`mt-6 flex gap-3 ${className}`}>{children}</div>;
}
