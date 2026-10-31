import React from "react";
import { useCurrentFrame } from "remotion";
import { evolvePath, getPointAtLength, getTangentAtLength, getLength } from "@remotion/paths";
import { colors, fonts, type } from "../theme";
import { ease } from "../anim";

/**
 * A path that draws itself with an arrowhead at the end. Optional dashed stroke
 * (read-only lines) and a label at the midpoint. Optional travelling dots.
 */
export const FlowArrow: React.FC<{
  d: string;
  delay?: number;
  duration?: number;
  color?: string;
  dashed?: boolean;
  label?: string;
  labelOffset?: { x: number; y: number };
  dots?: { count: number; period: number; start: number; end?: number };
  width?: number;
}> = ({ d, delay = 0, duration = 20, color = colors.line, dashed, label, labelOffset = { x: 0, y: -22 }, dots, width = 3 }) => {
  const frame = useCurrentFrame();
  const p = ease(frame, delay, duration);
  const evolved = evolvePath(p, d);
  const len = getLength(d);
  const zero = { x: 0, y: 0 };
  const end = getPointAtLength(d, len * p) ?? zero;
  const tan = getTangentAtLength(d, Math.max(0, len * p - 1)) ?? { x: 1, y: 0 };
  const angle = (Math.atan2(tan.y, tan.x) * 180) / Math.PI;
  const mid = getPointAtLength(d, len / 2) ?? zero;

  return (
    <>
      <svg style={{ position: "absolute", inset: 0, overflow: "visible", pointerEvents: "none" }} width="100%" height="100%">
        <path
          d={d}
          fill="none"
          stroke={color}
          strokeWidth={width}
          strokeLinecap="round"
          strokeDasharray={dashed ? "10 12" : evolved.strokeDasharray}
          strokeDashoffset={dashed ? undefined : evolved.strokeDashoffset}
          opacity={dashed ? p : 1}
        />
        {p > 0.02 ? (
          <polygon
            points="0,-8 14,0 0,8"
            fill={color}
            transform={`translate(${end.x} ${end.y}) rotate(${angle})`}
            opacity={p}
          />
        ) : null}
        {dots && frame >= dots.start && (dots.end === undefined || frame <= dots.end)
          ? Array.from({ length: dots.count }).map((_, i) => {
              const phase = (((frame - dots.start) / dots.period + i / dots.count) % 1 + 1) % 1;
              const pt = getPointAtLength(d, len * phase) ?? zero;
              return <circle key={i} cx={pt.x} cy={pt.y} r={6} fill={colors.accent} opacity={0.9} />;
            })
          : null}
      </svg>
      {label ? (
        <div
          style={{
            position: "absolute",
            left: mid.x + labelOffset.x,
            top: mid.y + labelOffset.y,
            translate: "-50% -50%",
            fontFamily: fonts.mono,
            fontSize: type.min,
            color: color === colors.line ? colors.textMuted : color,
            background: colors.bg,
            padding: "4px 10px",
            borderRadius: 8,
            whiteSpace: "nowrap",
            opacity: p,
          }}
        >
          {label}
        </div>
      ) : null}
    </>
  );
};
