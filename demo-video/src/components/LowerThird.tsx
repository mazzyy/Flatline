import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { colors, fonts, layout, type } from "../theme";
import { uiSpring } from "../anim";

/** Small title + subtitle in the bottom-left safe corner with an accent bar. */
export const LowerThird: React.FC<{
  title: string;
  sub?: string;
  delay?: number;
  color?: string;
  top?: number;
  left?: number;
  hideAfter?: number;
  /** Dark backing, for labels laid over a (light) dashboard clip. */
  backdrop?: boolean;
}> = ({
  title,
  sub,
  delay = 0,
  color = colors.accent,
  top,
  left,
  hideAfter,
  backdrop = false,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = uiSpring(frame, fps, delay);
  const leave = hideAfter === undefined ? 1 : 1 - uiSpring(frame, fps, hideAfter);
  return (
    <div
      style={{
        position: "absolute",
        left: left ?? layout.marginX,
        top: top ?? layout.marginY,
        display: "flex",
        gap: 18,
        alignItems: "stretch",
        opacity: p * leave,
        translate: `${(1 - p) * -24}px 0px`,
        ...(backdrop
          ? { padding: "14px 24px 14px 14px", borderRadius: 16, background: "rgba(9, 11, 16, 0.9)", boxShadow: "0 10px 30px rgba(0,0,0,0.35)" }
          : {}),
      }}
    >
      <div style={{ width: 6, borderRadius: 3, background: color }} />
      <div>
        <div style={{ fontFamily: fonts.body, fontWeight: 500, fontSize: type.label, color: colors.text, letterSpacing: "-0.01em" }}>{title}</div>
        {sub ? <div style={{ fontFamily: fonts.mono, fontSize: type.min, color: colors.textMuted, marginTop: 6 }}>{sub}</div> : null}
      </div>
    </div>
  );
};
