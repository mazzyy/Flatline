import React from "react";
import { AbsoluteFill, Composition } from "remotion";
import { DemoVideo, DemoVideoProps } from "./DemoVideo";
import { getTimeline } from "./timeline";
import { CLIP_FILES } from "./SceneContext";
import { layout } from "./theme";

const FPS = 30;

const clips = Object.fromEntries(CLIP_FILES.map((c) => [c, true]));

const defaultProps: DemoVideoProps = {
  scale: 1,
  hasVoiceover: false,
  hasMusic: false,
  clips,
};

const tl = getTimeline(FPS, 1);

/** 9:16 wrap: the 16:9 film, letterboxed. */
const DemoVideoVertical: React.FC<DemoVideoProps> = (props) => (
  <AbsoluteFill style={{ backgroundColor: "#0B0D12", justifyContent: "center", alignItems: "center" }}>
    <div style={{ width: 1080, height: 608, position: "relative", overflow: "hidden" }}>
      <div style={{ width: 1920, height: 1080, scale: String(1080 / 1920), transformOrigin: "top left" }}>
        <DemoVideo {...props} />
      </div>
    </div>
  </AbsoluteFill>
);

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="DemoVideo"
        component={DemoVideo}
        durationInFrames={tl.total}
        fps={FPS}
        width={layout.width}
        height={layout.height}
        defaultProps={defaultProps}
      />
      <Composition
        id="DemoVideoVertical"
        component={DemoVideoVertical}
        durationInFrames={tl.total}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={defaultProps}
      />
    </>
  );
};
