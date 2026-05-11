import React from "react";

export const Button = React.forwardRef(function Button(
  { asChild = false, className = "", type = "button", ...props },
  ref
) {
  if (asChild && React.isValidElement(props.children)) {
    return React.cloneElement(props.children, {
      className: [defaultClassName, className, props.children.props.className].filter(Boolean).join(" "),
    });
  }

  return <button ref={ref} type={type} className={[defaultClassName, className].filter(Boolean).join(" ")} {...props} />;
});

const defaultClassName =
  "inline-flex items-center justify-center rounded-xl border border-border/40 bg-white/10 px-4 py-2 text-sm font-medium text-white transition hover:bg-white/15 disabled:cursor-not-allowed disabled:opacity-50";
