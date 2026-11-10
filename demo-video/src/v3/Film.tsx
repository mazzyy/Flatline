import React, { useEffect, useState } from "react";
import { AbsoluteFill, continueRender, delayRender } from "remotion";
import { Captions } from "./Captions";
import { Hud } from "./Hud";
import { alive } from "./Pulse";
import { Close } from "./scenes/Close";
import { Demo } from "./scenes/Demo";
import { Open } from "./scenes/Open";
import { Recover } from "./scenes/Recover";
import { Title } from "./scenes/Title";
import { Trust } from "./scenes/Trust";
import { c, FONT_CHECKS } from "./theme";
import { useT } from "./time";

const GRAIN = `url("data:image/svg+xml;utf8,${encodeURIComponent(
  '<svg xmlns="http://www.w3.org/2000/svg" width="220" height="220"><filter id="n"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" stitchTiles="stitch"/><feColorMatrix values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 0.5 0"/></filter><rect width="220" height="220" filter="url(#n)"/></svg>',
)}")`;

export const Film: React.FC<{ captions?: boolean }> = ({ captions = true }) => {
  const t = useT();
  const [handle] = useState(() => delayRender("fonts"));
  useEffect(() => {
    Promise.all(FONT_CHECKS.map((font) => document.fonts.load(font))).then(() => continueRender(handle));
  }, [handle]);
  const glow = alive(t) ? c.alive : c.flat;
  return (
    <AbsoluteFill style={{ backgroundColor: c.bg, overflow: "hidden" }}>
      <AbsoluteFill style={{ background: `radial-gradient(1300px 700px at 50% 108%, ${glow}1f, transparent 70%)` }} />
      <AbsoluteFill style={{ backgroundImage: `linear-gradient(${c.line}55 1px, transparent 1px), linear-gradient(90deg, ${c.line}55 1px, transparent 1px)`, backgroundSize: "80px 80px", opacity: 0.35, maskImage: "radial-gradient(ellipse at center, black 30%, transparent 85%)", WebkitMaskImage: "radial-gradient(ellipse at center, black 30%, transparent 85%)" }} />
      <Open t={t} />
      <Title t={t} />
      <Demo t={t} />
      <Recover t={t} />
      <Trust t={t} />
      <Close t={t} />
      <Hud t={t} />
      {captions ? <Captions t={t} /> : null}
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,.55) 100%)", pointerEvents: "none" }} />
      <AbsoluteFill style={{ backgroundImage: GRAIN, opacity: 0.07, mixBlendMode: "overlay", pointerEvents: "none" }} />
    </AbsoluteFill>
  );
};
