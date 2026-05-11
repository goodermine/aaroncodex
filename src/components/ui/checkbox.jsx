export function Checkbox({ checked, onCheckedChange, ...props }) {
  return (
    <input
      type="checkbox"
      checked={!!checked}
      onChange={(event) => onCheckedChange?.(event.target.checked)}
      {...props}
    />
  );
}
