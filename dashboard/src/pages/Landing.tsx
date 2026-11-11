import type { ReactNode } from "react";
import Pulse from "../components/Pulse";
import { setInjectToken, setPasscode } from "../api";
import chaosImg from "../assets/guide/chaos.jpg";
import incidentImg from "../assets/guide/incident.jpg";
import recoveryImg from "../assets/guide/recovery.jpg";
import shopImg from "../assets/guide/shop.jpg";
import { useSite } from "../site";
import { useRevenue } from "../useRevenue";

const REPO = "https://github.com/mazzyy/Flatline";
// Set VITE_VIDEO_URL at build time to show the film link.
const VIDEO = (import.meta.env.VITE_VIDEO_URL as string | undefined) || "";

/** The front door: what this is, the two places to look, and a short guide to trying it. */
export default function Landing({ onEnter }: { onEnter: () => void }) {
  const { checkoutDown } = useRevenue();
  const { shopUrl, sandbox } = useSite();
  const here = location.host;
  const shopLabel = shopUrl.startsWith("/") ? `${here}${shopUrl}` : shopUrl.replace(/^https?:\/\//, "");

  const STEPS: { title: string; where: string; text: ReactNode; img: string; alt: string }[] = [
    {
      title: "Buy a coffee",
      where: "In the shop",
      text: (
        <>
          Open the shop, pick a bag and check out.{" "}
          {sandbox ? (
            <>
              Pay with a PayPal sandbox buyer, or press <b>Pay without a PayPal login (demo)</b> if you don&apos;t have one.
            </>
          ) : (
            <>
              Press <b>Pay (mock)</b>.
            </>
          )}{" "}
          The payment goes through.
        </>
      ),
      img: shopImg,
      alt: "The demo shop's catalogue with three coffees",
    },
    {
      title: "Break the checkout",
      where: "In the dashboard, under Chaos",
      text: (
        <>
          Log in, open <b>Chaos</b> and press <b>Ship bad currency config</b>. The shop now charges in euros, so payments fail. Try buying again in
          the shop: it is refused, and the line at the top of this page goes flat.
        </>
      ),
      img: chaosImg,
      alt: "The Chaos panel with the bad currency button",
    },
    {
      title: "Watch it find the cause, then approve the fix",
      where: "In the dashboard, under Overview",
      text: (
        <>
          An incident opens within seconds. Open it to read what broke and why. A warning banner is already on the shop. Press <b>Approve</b> on
          the rollback, and checkout works again.
        </>
      ),
      img: incidentImg,
      alt: "An incident page showing the root cause and the evidence",
    },
    {
      title: "Get the lost sales back",
      where: "On the same incident, about a minute later",
      text: (
        <>
          A recovery proposal appears with the customers whose payment failed. Approve it to send each one a PayPal invoice. Then, in{" "}
          <b>Chaos</b>, press <b>Customers pay their recovery requests</b> and watch <b>Recovered</b> on the Overview.
        </>
      ),
      img: recoveryImg,
      alt: "A recovery proposal listing six customers and the amount each tried to pay",
    },
  ];

  return (
    <div className="film">
      <header className="film-top">
        <span className="film-word">Flatline</span>
        <nav>
          <a href="#guide">How to try it</a>
          {VIDEO ? (
            <a href={VIDEO} target="_blank" rel="noreferrer">Watch the film</a>
          ) : null}
          <a href={REPO} target="_blank" rel="noreferrer">GitHub</a>
        </nav>
      </header>

      <section className="film-hero compact">
        <div className="film-hud">
          <span>LUMEN COFFEE CO. · REVENUE</span>
          <span className={`film-state ${checkoutDown ? "down" : ""}`}>
            <i />
            {checkoutDown ? "CHECKOUT DOWN" : "TAKING PAYMENTS"}
          </span>
        </div>
        <div className="film-pulse">
          <Pulse alive={!checkoutDown} height={130} seconds={7} stroke={3} />
        </div>
        <h1>
          On call for your <em>revenue.</em>
        </h1>
        <p className="film-sub">
          Flatline watches a shop&apos;s PayPal payments. When checkout breaks it notices, fixes it, and gets the lost sales back. This page is a
          live demo: the line above is this demo shop&apos;s checkout right now.
        </p>
      </section>

      <section className="film-section tight">
        <span className="film-label">THE DEMO HAS TWO PARTS</span>
        <div className="film-places">
          <article>
            <span className="film-num">1</span>
            <h3>The shop</h3>
            <p>Lumen Coffee Co., a made up coffee shop. This is where customers pay.</p>
            <a className="film-thumb" href={shopUrl} target="_blank" rel="noreferrer">
              <img src={shopImg} alt="The demo shop" />
            </a>
            <a className="film-btn" href={shopUrl} target="_blank" rel="noreferrer">Open the shop</a>
            <p className="film-fine">{shopLabel}</p>
          </article>
          <article>
            <span className="film-num">2</span>
            <h3>The dashboard</h3>
            <p>Where Flatline watches those payments, explains what went wrong, and waits for your approval.</p>
            <form
              className="film-login"
              onSubmit={(e) => {
                e.preventDefault();
                const fd = new FormData(e.currentTarget);
                setPasscode(String(fd.get("pass") || ""));
                setInjectToken(String(fd.get("inject") || "change-me"));
                onEnter();
              }}
            >
              <label htmlFor="pass">Passcode</label>
              <input id="pass" name="pass" defaultValue="demo-judge" />
              <label htmlFor="inject">Test token (unlocks the Chaos panel)</label>
              <input id="inject" name="inject" defaultValue="change-me" />
              <button type="submit" className="film-btn">Log in to the dashboard</button>
            </form>
            <p className="film-fine">{here} · both fields are filled in for you</p>
          </article>
        </div>
      </section>

      <section id="guide" className="film-section">
        <span className="film-label">TRY IT IN FIVE MINUTES</span>
        <h2>Break the shop, and watch what happens.</h2>
        <ol className="film-guide">
          {STEPS.map((s, i) => (
            <li key={s.title}>
              <div className="film-guide-text">
                <span className="film-num">{i + 1}</span>
                <h3>{s.title}</h3>
                <p className="film-where">{s.where}</p>
                <p>{s.text}</p>
              </div>
              <img src={s.img} alt={s.alt} />
            </li>
          ))}
        </ol>
        <p className="film-fine wide">
          To start again, press <b>Reset all chaos</b> in the Chaos panel. A second incident of the same kind within 30 minutes joins the first
          one, so wait a little before repeating a scenario.
        </p>
      </section>

      <section className="film-section tight">
        <div className="film-facts">
          <div>
            <h3>Nothing here costs money</h3>
            <p>It runs on the PayPal sandbox only. The code has no path to live PayPal.</p>
          </div>
          <div>
            <h3>The AI reads, code decides</h3>
            <p>The agents diagnose and propose. Plain code decides what may run, and anything that moves money waits for a person.</p>
          </div>
          <div>
            <h3>Open source</h3>
            <p>
              MIT licensed. The code, the tests and a benchmark are on <a href={REPO} target="_blank" rel="noreferrer">GitHub</a>.
            </p>
          </div>
        </div>
      </section>

      <footer className="film-foot">
        <span className="film-word">Flatline</span>
        <span className="film-serif">On call for your revenue.</span>
        <span>
          Built by Abdul Musawar Soomro for the PayPal AI Hackathon · <a href={REPO} target="_blank" rel="noreferrer">github.com/mazzyy/Flatline</a>
        </span>
      </footer>
    </div>
  );
}
