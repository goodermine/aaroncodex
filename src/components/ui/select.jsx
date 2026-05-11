import React, { createContext, useContext, useMemo, useState } from "react";

const SelectContext = createContext(null);

export function Select({ value, onValueChange, children }) {
  const [internalValue, setInternalValue] = useState(value || "");
  const contextValue = useMemo(
    () => ({
      value: value ?? internalValue,
      onValueChange: (next) => {
        setInternalValue(next);
        onValueChange?.(next);
      },
    }),
    [internalValue, onValueChange, value]
  );

  return <SelectContext.Provider value={contextValue}>{children}</SelectContext.Provider>;
}

export function SelectTrigger({ className = "", children }) {
  return <div className={`rounded-xl border border-border/40 bg-black/20 px-3 py-2 ${className}`}>{children}</div>;
}

export function SelectValue({ placeholder = "Select..." }) {
  const context = useContext(SelectContext);
  return <span>{context?.value || placeholder}</span>;
}

export function SelectContent({ children }) {
  return <div className="mt-2 grid gap-2">{children}</div>;
}

export function SelectItem({ value, children }) {
  const context = useContext(SelectContext);
  return (
    <button
      type="button"
      onClick={() => context?.onValueChange(value)}
      className={`rounded-lg border px-3 py-2 text-left text-sm ${
        context?.value === value ? "border-primary/50 bg-primary/10 text-primary" : "border-border/40 bg-black/20"
      }`}
    >
      {children}
    </button>
  );
}
