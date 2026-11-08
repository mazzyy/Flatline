"""Write the NARRATION block of src/captions.ts from narration.json (scene-relative times).

    python scripts/audio-v2/make-captions.py <vo-out>/narration.json
"""
import json
import re
import sys
from pathlib import Path

SCENE_STARTS = [0, 8, 18, 26, 71, 85, 107, 125, 140, 150]
TOTAL = 155.0
NAMES = ["S1", "S2", "S3", "Checkout demo", "How it works", "Refund wave", "Renewals", "Trust", "Built with", "Close"]

# Spoken form -> written form for the captions.
WRITTEN = {
    "over a hundred and twenty-nine billion dollars in twenty twenty-five": "over $129 billion in 2025",
}

rows = json.loads(Path(sys.argv[1]).read_text())
lines = ["export const NARRATION: Narration[] = ["]
for i, r in enumerate(rows):
    sc = r["scene"]
    s0 = SCENE_STARTS[sc]
    s_end = SCENE_STARTS[sc + 1] if sc + 1 < len(SCENE_STARTS) else TOTAL
    nxt = rows[i + 1] if i + 1 < len(rows) else None
    frm = max(0.0, r["start"] - s0 - 0.05)
    if nxt and nxt["scene"] == sc:
        to = nxt["start"] - s0 - 0.05
    else:
        to = min(r["end"] - s0 + 0.5, s_end - s0 - 0.05)
    if i == 0 or rows[i - 1]["scene"] != sc:
        lines.append(f"  // {NAMES[sc]}")
    text = r["text"]
    for spoken, written in WRITTEN.items():
        text = text.replace(spoken, written)
    text = text.replace('"', '\\"')
    lines.append(f'  {{ scene: {sc}, from: {frm:.2f}, to: {to:.2f}, text: "{text}" }},')
lines.append("];")
p = Path(__file__).resolve().parents[2] / "src" / "captions.ts"
src = p.read_text()
src = re.sub(r"export const NARRATION: Narration\[\] = \[.*?\n\];", "\n".join(lines), src, flags=re.S)
p.write_text(src)
print(f"wrote {len(rows)} caption segments")
