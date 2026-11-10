import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/600.css";
import "@fontsource/inter/700.css";
import "@fontsource/inter/800.css";
import "@fontsource/jetbrains-mono/400.css";
import "@fontsource/jetbrains-mono/600.css";
import "@fontsource/instrument-serif/400.css";
import "@fontsource/instrument-serif/400-italic.css";

/** One palette for the whole film. The pulse owns green and red; nothing else may use them. */
export const c = {
  bg: "#07090C",
  panel: "#0F1318",
  panel2: "#161B22",
  line: "#232A34",
  text: "#F4F1EA",
  dim: "#9AA3AF",
  faint: "#5B6470",
  alive: "#3DDC97",
  flat: "#FF4D4D",
  warn: "#F5B83D",
  blue: "#5B9DFF",
  paper: "#F4F1EA",
  ink: "#101418",
} as const;

export const f = {
  sans: '"Inter", system-ui, sans-serif',
  mono: '"JetBrains Mono", ui-monospace, monospace',
  serif: '"Instrument Serif", Georgia, serif',
} as const;

export const FPS = 30;
export const W = 1920;
export const H = 1080;

export const FONT_CHECKS = [
  '400 20px "Inter"',
  '600 20px "Inter"',
  '800 20px "Inter"',
  '400 20px "JetBrains Mono"',
  '600 20px "JetBrains Mono"',
  '400 20px "Instrument Serif"',
  'italic 400 20px "Instrument Serif"',
];
