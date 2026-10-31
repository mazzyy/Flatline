import React from "react";
import { AbsoluteFill, OffthreadVideo, staticFile } from "remotion";
import { colors, fonts, type } from "../theme";

/**
 * Plays a screen recording from public/clips, or a clearly labelled placeholder
 * when the file is missing so timing stays intact.
 */
export const Clip: React.FC<{
  name: string;
  available: boolean;
  trimBefore?: number;
  playbackRate?: number;
  objectPosition?: string;
}> = ({ name, available, trimBefore, playbackRate = 1, objectPosition = "top left" }) => {
  if (!available) {
    return (
      <AbsoluteFill
        style={{
          background: colors.surface,
          border: `2px dashed ${colors.line}`,
          margin: 16,
          borderRadius: 12,
          alignItems: "center",
          justifyContent: "center",
          fontFamily: fonts.mono,
          fontSize: type.label,
          color: colors.textMuted,
        }}
      >
        CLIP: {name.replace(/\.mp4$/, "")}
      </AbsoluteFill>
    );
  }
  return (
    <OffthreadVideo
      src={staticFile(`clips/${name}`)}
      muted
      trimBefore={trimBefore}
      playbackRate={playbackRate}
      style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition }}
    />
  );
};
