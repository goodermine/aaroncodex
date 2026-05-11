import React from "react";

export const ScrollArea = React.forwardRef(function ScrollArea({ className = "", children }, ref) {
  return (
    <div ref={ref} className={`overflow-auto ${className}`}>
      <div data-radix-scroll-area-viewport>{children}</div>
    </div>
  );
});
