import React from "react";
import { AbsoluteFill, Sequence, useCurrentFrame, useVideoConfig } from "remotion";
import { Background } from "../components/Background";
import { BrowserFrame } from "../components/BrowserFrame";
import { Clip } from "../components/Clip";
import { Highlight } from "../components/Highlight";
import { LowerThird } from "../components/LowerThird";
import { colors, fonts, layout, type } from "../theme";
import { accentSpring, ease, uiSpring } from "../anim";
import { useClips, useT } from "../SceneContext";
import { CLIP_H, CLIP_W } from "./S5Checkout";

const CHECKS = [
  "Sandbox only — live PayPal cannot start",
  "Agents never hold write credentials",
  "Unknown actions are forbidden",
  "Every step audited",
];

const GRID = "09-transactions.mp4";
/** The Simulated column in 09-transactions.mp4 (clip pixels); re-measure after recording. */
const GRID_SIMULATED = { x0: 996, y0: 300, x1: 1090, y1: 856 };

export const S8Trust: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = useT();
  const clips = useClips();
  const frameC = { x: layout.marginX, y: 180, w: 1000 };
  const colX = 1180;
  const at = [t(0.8), t(5.0), t(7.2), t(9.0)];
  const frameH = 44 + (frameC.w * CLIP_H) / CLIP_W;
  // The transactions grid shows first, when its clip has been recorded, then the audit log.
  const grid = Boolean(clips[GRID]);
  const gridEnd = t(6.6);

  return (
    <AbsoluteFill>
      <Background glow="ok" glowStrength={0.12} />
      {grid ? (
        <>
          <div style={{ opacity: 1 - ease(frame, gridEnd - 6, 10) }}>
            <LowerThird title="Transactions · AG Grid" sub="server side rows · injected events marked simulated" delay={t(0.2)} top={90} color={colors.accent} />
          </div>
          <div style={{ position: "absolute", inset: 0, opacity: 1 - ease(frame, gridEnd - 4, 10) }}>
            <BrowserFrame x={frameC.x} y={frameC.y} width={frameC.w} height={frameH} url="localhost:8000/#/transactions" delay={t(0.1)}>
              <Clip name={GRID} available />
            </BrowserFrame>
            <Highlight box={GRID_SIMULATED} from={t(1.2)} to={gridEnd - 8} label="injected events marked simulated" color={colors.warn} frame={frameC} labelSide="above" />
          </div>
        </>
      ) : null}
      <Sequence from={grid ? gridEnd - 4 : 0} layout="none">
        <div style={{ opacity: grid ? ease(frame, gridEnd - 4, 10) : 1 }}>
          <LowerThird title="Audit log" sub="every decision, actor and reason" delay={grid ? 6 : t(0.2)} top={90} color={colors.ok} />
        </div>
        <div style={{ position: "absolute", inset: 0, opacity: grid ? ease(frame, gridEnd - 4, 10) : 1 }}>
          <BrowserFrame x={frameC.x} y={frameC.y} width={frameC.w} height={frameH} url="localhost:8000/#/audit" delay={grid ? 0 : t(0.1)}>
            <Clip name="08-audit-log.mp4" available={Boolean(clips["08-audit-log.mp4"])} />
          </BrowserFrame>
        </div>
      </Sequence>

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
