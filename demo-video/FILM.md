# Flatline film (November cut)

`out/flatline-film.mp4`: 1920×1080, 30 fps, 2:41, H.264 + AAC at -15 LUFS. Under the three minute limit.
`out/flatline-film-no-voice.mp4`: the same picture with music and effects only, for recording your own voice.

It is a separate Remotion entry point (`src/v3/index.tsx`) and does not touch the earlier cut in `src/`.
Fonts are bundled from `@fontsource`, so it renders offline.

```
npm install
npx remotion render src/v3/index.tsx Film out/picture.mp4 --codec=h264 --crf=18 --jpeg-quality=90 --muted
python scripts/audio-v3/voice.py am_michael 0.95      # narration + timings (needs kokoro-onnx and its model files)
python scripts/audio-v3/score.py src/v3/vo.json scripts/audio-v3/out/voice-am_michael.wav out/   # score, effects, mix
ffmpeg -i out/picture.mp4 -i out/mix.wav -map 0:v -map 1:a -c:v copy -af loudnorm=I=-15:TP=-1.5 -c:a aac -b:a 256k out/flatline-film.mp4
```

## How it is put together

- **One idea carries the film.** The shop's revenue is a heartbeat (`src/v3/Pulse.tsx`): green and beating while
  people pay, red and flat while checkout is down. It flatlines in the open, comes back at the approve click, and
  beats once for each customer who pays a recovery invoice. The score runs at the same tempo as the beat.
- **Every picture beat hangs off the narration.** `src/v3/vo.json` holds each line's start and end; `src/v3/time.ts`
  turns them into cues. Change a line, re-run `voice.py`, copy the new `vo-*.json` over `src/v3/vo.json`, and the
  picture and the score follow.
- **Screens.** `public/v3/` holds the stills. The incident (overview excepted) is from the earlier sandbox and Gemini
  recordings. The overview and the recovery screens were shot from the app in mock mode after the recovery step
  was built; no model names are in frame there.
- **AG Grid.** The six failed payments are shown in the transactions grid (`public/v3/aggrid.jpg`, mock mode) before they become the recovery list.
- **The real invoice.** `invoice-real.jpg` and `invoice-paid.jpg` are screenshots of invoice INV2-Y94L-ETFU-ZUZA-PB57,
  sent by `scripts/sandbox_invoice.py` through the PayPal MCP server and paid by a sandbox buyer on 10 Nov 2026.
- **Honesty on screen.** The small print says one invoice was sent and paid for real and the four counted payments
  are simulated, and the benchmark card says it ran with stand-in models.
- **Sound.** Voice is Kokoro `am_michael` at 0.95 speed. Music and effects are synthesized in `score.py`; nothing is licensed.

The narration with its timings is in `scripts/audio-v3/SCRIPT.md`.
