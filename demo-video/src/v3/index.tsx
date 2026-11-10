import React from "react";
import { Composition, registerRoot } from "remotion";
import { Film } from "./Film";
import { FPS, H, W } from "./theme";
import { TOTAL } from "./time";

/** Entry point of the 2026-11 cut. Fonts are bundled, so it renders offline. */
const Root: React.FC = () => (
  <Composition id="Film" component={Film} durationInFrames={Math.round(TOTAL * FPS)} fps={FPS} width={W} height={H} defaultProps={{ captions: true }} />
);
registerRoot(Root);
