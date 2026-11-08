import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { Background } from "../components/Background";
import { KineticHeadline } from "../components/KineticHeadline";
import { StatCounter } from "../components/StatCounter";
import { colors, fonts, layout, type } from "../theme";
import { ease, uiSpring } from "../anim";
import { useT } from "../SceneContext";

export const S2Problem: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = useT();

  const x0 = layout.marginX;
  const x1 = layout.width - layout.marginX;
  const y = 640;
  const friX = x0 + (x1 - x0) * 0.22;
  const monX = x0 + (x1 - x0) * 0.86;

  const copyAt = t(0.3);
  const axisAt = t(1.0);
  const friAt = t(1.8);
  const growFrom = t(2.6);
  const growFor = t(7.4);
  const monAt = growFrom + growFor;
  const noticedAt = t(11.6);

  const axis = ease(frame, axisAt, 24);
  const grow = ease(frame, growFrom, growFor);
  const fri = uiSpring(frame, fps, friAt);
  const mon = uiSpring(frame, fps, monAt);
  const areaH = 180;
  const days = ["Fri", "Sat", "Sun", "Mon"];

  return (
    <AbsoluteFill>
      <Background glow="critical" glowStrength={0.1 + grow * 0.14} />

      <div style={{ position: "absolute", left: x0, top: layout.marginY, width: 1100 }}>
        <KineticHeadline text="A broken checkout. A refund wave. A failing renewal." size={type.h2} delay={copyAt} />
      </div>

      <div style={{ position: "absolute", right: x0, top: layout.marginY - 8 }}>
        <StatCounter value={129} prefix="$" suffix="B" label="failed payments could cost subscription companies in 2025" note="Recurly estimate" delay={growFrom} duration={growFor} size={type.h1Large} color={colors.critical} align="right" />
      </div>

      {/* Red area between break and discovery */}
      <div
        style={{
          position: "absolute",
          left: friX,
          top: y - areaH,
          width: (monX - friX) * grow,
          height: areaH,
          background: `linear-gradient(180deg, ${colors.critical}55, ${colors.critical}08)`,
          borderTop: `2px solid ${colors.critical}`,
          borderRadius: "0 8px 0 0",
        }}
      />

      {/* Axis */}
      <div style={{ position: "absolute", left: x0, top: y, width: (x1 - x0) * axis, height: 2, background: colors.line }} />
      {days.map((d, i) => {
        const dx = x0 + (x1 - x0) * (0.22 + i * 0.2133);
        return (
          <div key={d} style={{ position: "absolute", left: dx, top: y + 16, translate: "-50% 0", opacity: axis, fontFamily: fonts.mono, fontSize: type.min, color: colors.textMuted }}>
            {d}
          </div>
        );
      })}

      {/* Markers */}
      <Marker x={friX} y={y} p={fri} title="Checkout breaks" time="Fri 18:00" above={false} />
      <Marker x={monX} y={y} p={mon} title="Discovered" time="Mon 09:00" above={false} />

      <div style={{ position: "absolute", left: x0, top: 860, width: 1400 }}>
        <KineticHeadline text="Noticed days later." size={type.h1} delay={noticedAt} color={colors.critical} />
      </div>
    </AbsoluteFill>
  );
};

const Marker: React.FC<{ x: number; y: number; p: number; title: string; time: string; above: boolean }> = ({ x, y, p, title, time }) => (
  <div style={{ position: "absolute", left: x, top: y, opacity: p }}>
    <div style={{ position: "absolute", left: -10, top: -10, width: 20, height: 20, borderRadius: 10, background: colors.critical, boxShadow: `0 0 0 ${6 * p}px ${colors.critical}33`, scale: String(interpolate(p, [0, 1], [0.4, 1])) }} />
    <div style={{ position: "absolute", left: -1, top: 10, width: 2, height: 60, background: colors.critical, opacity: 0.6 }} />
    <div style={{ position: "absolute", left: 0, top: 52, translate: "-50% 0", textAlign: "center", whiteSpace: "nowrap" }}>
      <div style={{ fontFamily: fonts.body, fontWeight: 500, fontSize: type.label, color: colors.text }}>{title}</div>
      <div style={{ fontFamily: fonts.mono, fontSize: type.min, color: colors.textMuted, marginTop: 4 }}>{time}</div>
    </div>
  </div>
);
