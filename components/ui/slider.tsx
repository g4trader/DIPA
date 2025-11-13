
"use client";
import * as React from "react";
export function Slider({ defaultValue = [0], max = 10, step = 1, onValueChange }: any) {
  const [val, setVal] = React.useState(defaultValue[0]);
  return (
    <input
      type="range"
      min={0}
      max={max}
      step={step}
      value={val}
      onChange={(e) => {
        const v = Number(e.target.value);
        setVal(v);
        onValueChange?.([v]);
      }}
      className="w-full cursor-pointer accent-blue-500"
    />
  );
}
