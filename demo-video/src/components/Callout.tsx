import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { evolvePath } from "@remotion/paths";
import { colors, fonts, radius, type } from "../theme";
import { ease, uiSpring } from "../anim";

/**
 * Pill label with a leader line that draws itself to a target point, plus a
 * highlight ring at the target. Coordinates are in the parent's space.
 */
export const Callout: React.FC<{
  label: string;
  target: { x: number; y: number };
  at: { x: number; y: number };
  delay?: number;
  color?: string;
  ring?: { w: number; h: number; r?: number };
  hideAfter?: number;
  /** Centre of the highlight ring, if it should not sit on the leader's end point. */
  ringAt?: { x: number; y: number };
  /** Fades the pill and leader only (dot and ring stay), e.g. while a camera is zoomed in. */
  labelOpacity?: number;
}> = ({ label, target, at, delay = 0, color = colors.accent, ring, hideAfter, ringAt, labelOpacity = 1 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = uiSpring(frame, fps, delay);
  const draw = ease(frame, delay + 6, 18);
  const leave = hideAfter === undefined ? 1 : 1 - ease(frame, hideAfter, 10);
  const pillH = 52;
  // Leader from pill edge to target, with a soft bend.
  const start = { x: at.x, y: at.y + pillH / 2 };
  const mid = { x: (start.x + target.x) / 2, y: start.y };
  const d = `M ${start.x} ${start.y} Q ${mid.x} ${mid.y} ${target.x} ${target.y}`;
  const evolved = evolvePath(draw, d);

  return (
    <div style={{ position: "absolute", inset: 0, pointerEvents: "none", opacity: leave }}>
      <svg style={{ position: "absolute", inset: 0, overflow: "visible" }} width="100%" height="100%">
        <path
          d={d}
          fill="none"
          stroke={color}
          strokeWidth={3}
          strokeLinecap="round"
          strokeDasharray={evolved.strokeDasharray}
          strokeDashoffset={evolved.strokeDashoffset}
          opacity={labelOpacity}
        />
        <circle cx={target.x} cy={target.y} r={7 * draw} fill={color} />
        {ring ? (
          <rect
            x={(ringAt ?? target).x - ring.w / 2}
            y={(ringAt ?? target).y - ring.h / 2}
            width={ring.w}
            height={ring.h}
            rx={ring.r ?? 10}
            fill="none"
            stroke={color}
            strokeWidth={3}
            opacity={draw}
          />
        ) : null}
      </svg>
      <div
        style={{
          position: "absolute",
          left: at.x,
          top: at.y - pillH / 2,
          height: pillH,
          padding: "0 22px",
          display: "flex",
          alignItems: "center",
          borderRadius: radius.pill,
          background: color,
          color: colors.bg,
          fontFamily: fonts.body,
          fontWeight: 500,
          fontSize: type.labelSmall,
          whiteSpace: "nowrap",
          opacity: enter * labelOpacity,
          scale: String(0.9 + enter * 0.1),
          transformOrigin: "left center",
          boxShadow: `0 8px 24px ${color}55`,
        }}
      >
        {label}
      </div>
    </div>
  );
};
