import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { Background } from "../components/Background";
import { BrowserFrame } from "../components/BrowserFrame";
import { Clip } from "../components/Clip";
import { LowerThird } from "../components/LowerThird";
import { colors, fonts, layout, type } from "../theme";
import { accentSpring, uiSpring } from "../anim";
import { useClips, useT } from "../SceneContext";
import { CLIP_H, CLIP_W } from "./S5Checkout";

const CHECKS = [
  "Sandbox only — live PayPal cannot start",
  "Agents never hold write credentials",
  "Unknown actions are forbidden",
  "Every step audited",
];

export const S8Trust: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = useT();
  const clips = useClips();
  const frameC = { x: layout.marginX, y: 180, w: 1000 };
  const colX = 1180;
  const at = [t(0.8), t(5.0), t(7.2), t(9.0)];

  return (
    <AbsoluteFill>
      <Background glow="ok" glowStrength={0.12} />
      <LowerThird title="Audit log" sub="every decision, actor and reason" delay={t(0.2)} top={90} color={colors.ok} />
      <BrowserFrame x={frameC.x} y={frameC.y} width={frameC.w} height={44 + (frameC.w * CLIP_H) / CLIP_W} url="localhost:8000/#/audit" delay={t(0.1)}>
        <Clip name="08-audit-log.mp4" available={Boolean(clips["08-audit-log.mp4"])} />
      </BrowserFrame>

      <div style={{ position: "absolute", left: colX, top: 250, width: 620, display: "flex", flexDirection: "column", gap: 34 }}>
        {CHECKS.map((c, i) => {
          const p = uiSpring(frame, fps, at[i]);
          const tick = accentSpring(frame, fps, at[i] + 6);
          return (
            <div key={c} style={{ display: "flex", gap: 20, alignItems: "flex-start", opacity: p, translate: `0px ${(1 - p) * 24}px` }}>
              <div
                style={{
                  width: 44,
                  height: 44,
                  borderRadius: 12,
                  flexShrink: 0,
                  background: `${colors.ok}1f`,
                  border: `1px solid ${colors.ok}`,
                  display: "grid",
                  placeItems: "center",
                }}
              >
                <svg width="26" height="26" viewBox="0 0 24 24" style={{ scale: String(Math.min(1, tick)), opacity: Math.min(1, tick) }}>
                  <path d="M4 12l5 5L20 6" stroke={colors.ok} strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
              <div style={{ fontFamily: fonts.body, fontWeight: 500, fontSize: type.label, color: colors.text, lineHeight: 1.3, paddingTop: 4 }}>{c}</div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
