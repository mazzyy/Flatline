import React from "react";
import { AbsoluteFill, Audio, staticFile, useVideoConfig } from "remotion";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { getTimeline, SCENES, TRANSITION_FRAMES } from "./timeline";
import { getCaptionSegments } from "./captions";
import { CaptionTrack } from "./components/CaptionTrack";
import { ClipAvailability, SceneProvider } from "./SceneContext";
import { colors } from "./theme";
import { S1Hook } from "./scenes/S1Hook";
import { S2Problem } from "./scenes/S2Problem";
import { S3Intro } from "./scenes/S3Intro";
import { S4Architecture } from "./scenes/S4Architecture";
import { S5Checkout } from "./scenes/S5Checkout";
import { S6Refunds } from "./scenes/S6Refunds";
import { S7Renewals } from "./scenes/S7Renewals";
import { S8Trust } from "./scenes/S8Trust";
import { S9BuiltWith } from "./scenes/S9BuiltWith";
import { S10Close } from "./scenes/S10Close";

export type DemoVideoProps = {
  /** 1 = 170 s. >1 when the voiceover is longer; every scene stretches proportionally. */
  scale: number;
  /** Lay the final mix (voice + music + SFX, public/audio/soundtrack-v2.m4a) under the picture. */
  hasSoundtrack: boolean;
  clips: ClipAvailability;
};

const SCENE_COMPONENTS: React.FC[] = [S1Hook, S2Problem, S3Intro, S4Architecture, S5Checkout, S6Refunds, S7Renewals, S8Trust, S9BuiltWith, S10Close];

export const DemoVideo: React.FC<DemoVideoProps> = ({ scale, hasSoundtrack, clips }) => {
  const { fps } = useVideoConfig();
  const tl = getTimeline(fps, scale);
  const captions = getCaptionSegments(fps, scale);

  return (
    <SceneProvider value={{ scale, clips }}>
      <AbsoluteFill style={{ backgroundColor: colors.bg }}>
        <TransitionSeries>
          {SCENES.map((scene, i) => {
            const Scene = SCENE_COMPONENTS[i];
            return (
              <React.Fragment key={scene.id}>
                <TransitionSeries.Sequence name={`${scene.id.toUpperCase()} ${scene.name}`} durationInFrames={tl.sequenceFrames[i]}>
                  <Scene />
                </TransitionSeries.Sequence>
                {i < SCENES.length - 1 ? (
                  <TransitionSeries.Transition presentation={fade()} timing={linearTiming({ durationInFrames: TRANSITION_FRAMES })} />
                ) : null}
              </React.Fragment>
            );
          })}
        </TransitionSeries>
        <CaptionTrack segments={captions} />
        {hasSoundtrack ? <Audio src={staticFile("audio/soundtrack-v2.m4a")} /> : null}
      </AbsoluteFill>
    </SceneProvider>
  );
};
