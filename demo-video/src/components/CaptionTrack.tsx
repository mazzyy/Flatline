import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { colors, fonts, type } from "../theme";

export type CaptionSegment = { from: number; to: number; text: string };

/**
 * Burned-in captions: bottom centre, max two lines, 34px, on a 70% bg pill.
 * `segments` are absolute frames in the composition.
 */
export const CaptionTrack: React.FC<{ segments: CaptionSegment[]; bottom?: number }> = ({ segments, bottom = 72 }) => {
  const frame = useCurrentFrame();
  const { width } = useVideoConfig();
  const active = segments.find((s) => frame >= s.from && frame < s.to);
  if (!active) return null;
  const fadeIn = interpolate(frame, [active.from, active.from + 6], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const fadeOut = interpolate(frame, [active.to - 6, active.to], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const o = Math.min(fadeIn, fadeOut);
  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        bottom,
        display: "flex",
        justifyContent: "center",
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          maxWidth: Math.min(1400, width - 240),
          padding: "14px 30px",
          borderRadius: 18,
          background: "rgba(11, 13, 18, 0.7)",
          backdropFilter: "blur(6px)",
          fontFamily: fonts.body,
          fontWeight: 500,
          fontSize: type.caption,
          lineHeight: 1.3,
          color: colors.text,
          textAlign: "center",
          opacity: o,
          translate: `0px ${(1 - fadeIn) * 10}px`,
        }}
      >
        {active.text}
      </div>
    </div>
  );
};
