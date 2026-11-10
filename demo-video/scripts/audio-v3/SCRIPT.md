# Flatline film: narration script

25 lines, 161 seconds. Every picture beat is timed to these starts
(`src/v3/vo.json`), so a re-recorded voice should start each line at the time shown and
finish within the length shown. Pauses between lines are part of the film: leave them.

To use your own voice: play `out/flatline-film-no-voice.mp4`, record each line against it,
export one WAV of the whole read (24 kHz mono, 161.4 s), then run
`python scripts/audio-v3/score.py src/v3/vo.json your-voice.wav out/` and put `out/mix.wav`
under the picture with `ffmpeg -i picture.mp4 -i out/mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k film.mp4`.

How to read it: quietly, like telling a friend what happened. Slow down on the lines in
the open, leave a full breath before "One click." and before "$72. Back.".

| Starts | Length | Line |
| --- | --- | --- |
| 0:01.4 | 4.7 s | This line is a coffee shop's revenue. Every beat is somebody paying. |
| 0:07.3 | 4.3 s | Friday evening, a config change goes out... and checkout breaks. |
| 0:13.5 | 3.7 s | The servers are fine. Nobody finds out until Monday. |
| 0:18.2 | 4.6 s | We put people on call for servers. Nobody is on call for the money. |
| 0:24.7 | 4.9 s | So I built Flatline. An on-call engineer for your PayPal revenue. |
| 0:30.5 | 6.6 s | Let me break my own shop. One bad config, and this American store now charges in euros. |
| 0:38.3 | 8.3 s | Payments start failing. Within seconds, Flatline opens an incident, and puts a number on it: the money at risk, every hour. |
| 0:47.5 | 9.5 s | Then four AI agents go to work. One of them reads the real transactions from PayPal, through PayPal's own MCP server. |
| 0:58.0 | 6.3 s | And it finds the cause, with evidence. Not the bank. Not PayPal. Our own config change. |
| 1:05.1 | 4.5 s | The warning banner, it put up by itself. But the rollback waits for me. |
| 1:11.0 | 1.0 s | One click. |
| 1:14.1 | 1.1 s | And we're back. |
| 1:17.6 | 4.4 s | Most tools stop here. Incident resolved, everybody goes home. |
| 1:22.9 | 5.8 s | But six people tried to buy coffee while we were down. That's $108, gone. |
| 1:29.5 | 9.9 s | Flatline goes after it. It finds those six customers, and with one more approval, sends each of them a PayPal invoice, with an apology. |
| 1:42.1 | 3.5 s | In this demo, I play the customers. Four of them pay. |
| 1:47.9 | 2.0 s | $72. Back. |
| 1:51.0 | 8.1 s | And no AI writes those invoices. That part is plain code, because a model should never get to invent an amount. |
| 2:01.0 | 4.6 s | That's the rule everywhere. The agents can only ask. Code decides. |
| 2:06.3 | 3.3 s | I tried to sneak in a bulk refund. Refused. |
| 2:10.3 | 7.5 s | Safe fixes run on their own. Anything that moves money waits for a human. And refunds have a daily budget. |
| 2:18.6 | 3.6 s | And a benchmark attacks all of it. 34 checks. |
| 2:23.9 | 5.1 s | Built on PayPal's sandbox, MCP server, webhooks and invoicing. |
| 2:29.9 | 5.0 s | It notices when your checkout breaks, fixes it, and gets the lost sales back. |
| 2:36.4 | 2.3 s | Flatline. On call for your revenue. |
