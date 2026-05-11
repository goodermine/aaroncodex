export function Slider({ value = [0], onValueChange, min = 0, max = 100, step = 1, className = "" }) {
  const currentValue = Array.isArray(value) ? value[0] : value;

  return (
    <input
      type="range"
      min={min}
      max={max}
      step={step}
      value={currentValue}
      onChange={(event) => onValueChange?.([Number(event.target.value)])}
      className={`w-full ${className}`}
    />
  );
}
