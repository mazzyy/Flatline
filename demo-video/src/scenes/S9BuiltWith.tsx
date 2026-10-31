import React from "react";
import { AbsoluteFill } from "remotion";
import { Background } from "../components/Background";
import { KineticHeadline } from "../components/KineticHeadline";
import { Chip } from "../components/Chip";
import { colors, type } from "../theme";
import { useT } from "../SceneContext";

const STACK = [
  "PayPal REST",
  "PayPal MCP server",
  "PayPal JS SDK v6",
  "Webhooks",
  "Azure OpenAI",
  "Python",
  "FastAPI",
  "React",
  "AG Grid",
  "Render",
];

export const S9BuiltWith: React.FC = () => {
  const t = useT();
  return (
    <AbsoluteFill>
      <Background glow="accent" glowStrength={0.16} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", translate: "0px -30px" }}>
          <KineticHeadline text="Built with" size={type.h2} delay={t(0.2)} color={colors.textMuted} font="body" weight={400} align="center" />
          <div style={{ marginTop: 48, display: "flex", flexWrap: "wrap", justifyContent: "center", gap: 22, width: 1400 }}>
            {STACK.map((s, i) => (
              <Chip key={s} text={s} delay={t(0.9) + i * 5} size={type.label} color={i < 4 ? colors.accent : colors.textMuted} />
            ))}
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
