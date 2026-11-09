import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { colors, fonts, radius, type } from "../theme";
import { ease, uiSpring } from "../anim";
import { STAGE, STAGE_H, onStage } from "./Stage";

/** A box in clip pixels (1600x900): left, top, right, bottom. */
export type ClipBox = { x0: number; y0: number; x1: number; y1: number };

/**
 * Points at part of a clip without moving the camera: a ring around the box,
 * the rest of the page dimmed a little, and a short label on the ring.
 * Render it inside the stage's camera wrapper so it moves with the clip.
 */
export const Highlight: React.FC<{
  box: ClipBox;
  /** Scene frames. */
  from: number;
  to: number;
  label?: string;
  color?: string;
  /** Where the label sits: above (default), below, right of the box, or inside its top-right corner. */
  labelSide?: "above" | "below" | "right" | "inside";
  /** How much the rest of the page dims, 0 to 1. */
  dim?: number;
  /** Follow a scroll in the clip: shift by dy clip pixels between scene frames at and at + dur. */
  move?: { at: number; dur: number; dy: number };
}> = ({ box, from, to, label, color = colors.accent, labelSide = "above", dim = 0.28, move }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (frame < from - 2 || frame > to + 12) return null;
  const pad = 8;
  const dy = move ? move.dy * Math.min(1, Math.max(0, (frame - move.at) / Math.max(1, move.dur))) : 0;
  const a = onStage({ x: box.x0, y: box.y0 + dy });
  const b = onStage({ x: box.x1, y: box.y1 + dy });
  const r = { x: a.x - pad, y: a.y - pad, w: b.x - a.x + pad * 2, h: b.y - a.y + pad * 2 };
  const enter = uiSpring(frame, fps, from);
  const leave = 1 - ease(frame, to, 10);
  const o = enter * leave;
  const grow = 1.04 - 0.04 * enter;
  const pillH = 46;
  const pillPos: React.CSSProperties =
    labelSide === "above"
      ? { left: r.x, top: r.y - pillH - 10 }
      : labelSide === "below"
        ? { left: r.x, top: r.y + r.h + 10 }
        : labelSide === "right"
          ? { left: r.x + r.w + 14, top: r.y + r.h / 2 - pillH / 2 }
          : { right: 1920 - (r.x + r.w) + 14, top: r.y + 12 };
  return (
    <div style={{ position: "absolute", inset: 0, pointerEvents: "none" }}>
      {/* Dim the stage outside the box (clipped to the stage, so the frame around it is untouched). */}
      <div style={{ position: "absolute", left: STAGE.x, top: STAGE.y, width: STAGE.w, height: STAGE_H, overflow: "hidden", borderRadius: 14 }}>
        <div
          style={{
            position: "absolute",
            left: r.x - STAGE.x,
            top: r.y - STAGE.y,
            width: r.w,
            height: r.h,
            borderRadius: 12,
            boxShadow: `0 0 0 4000px rgba(8, 10, 15, ${dim * o})`,
          }}
        />
      </div>
      <div
        style={{
          position: "absolute",
          left: r.x,
          top: r.y,
          width: r.w,
          height: r.h,
          borderRadius: 12,
          border: `3.5px solid ${color}`,
          boxShadow: `0 0 0 6px ${color}2e, 0 0 28px ${color}55`,
          opacity: o,
          scale: String(grow),
        }}
      />
      {label ? (
        <div
          style={{
            position: "absolute",
            ...pillPos,
            height: pillH,
            padding: "0 20px",
            display: "flex",
            alignItems: "center",
            borderRadius: radius.pill,
            background: color,
            color: colors.bg,
            fontFamily: fonts.body,
            fontWeight: 500,
            fontSize: type.min,
            whiteSpace: "nowrap",
            boxShadow: "0 8px 24px rgba(0,0,0,0.3)",
            opacity: o,
            translate: `0px ${(1 - enter) * (labelSide === "below" ? -10 : 10)}px`,
          }}
        >
          {label}
        </div>
      ) : null}
    </div>
  );
};
