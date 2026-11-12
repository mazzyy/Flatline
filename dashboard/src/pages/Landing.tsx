import type { ReactNode } from "react";
import Pulse from "../components/Pulse";
import { setInjectToken, setPasscode } from "../api";
import chaosImg from "../assets/guide/chaos.jpg";
import incidentImg from "../assets/guide/incident.jpg";
import recoveryImg from "../assets/guide/recovery.jpg";
import shopImg from "../assets/guide/shop.jpg";
import { useSite } from "../site";
import { cash, useRevenue } from "../useRevenue";

const REPO = "https://github.com/mazzyy/Flatline";
// VITE_VIDEO_URL at build time overrides the film link.
const VIDEO = (import.meta.env.VITE_VIDEO_URL as string | undefined) || "https://www.youtube.com/watch?v=mnbAXQDoEko";

const WHAT: [string, string, string][] = [
  ["Detect", "Within seconds", "It watches PayPal webhooks and the shop's checkout. When failures jump, an incident opens with the money at risk per hour."],
  ["Diagnose", "Four AI agents, read only", "They read the payments, the shop's settings and PayPal itself, and name the cause with evidence."],
  ["Fix", "One click", "Safe fixes run on their own. Anything that changes the shop or moves money waits for you."],
  ["Recover", "Plain code, no AI", "Once the fix holds, it finds the customers who could not pay and sends each one a PayPal invoice."],
];

const TIERS: [string, string, string[]][] = [
  ["auto", "runs on its own", ["Warning banner", "Alert the merchant", "Payment reminder"]],
  ["approval", "waits for a human", ["Config rollback", "Recovery invoices", "A refund up to the limit"]],
  ["forbidden", "refused, always", ["Bulk refunds", "Payouts", "Anything not on the list"]],
];

/** The front door: the pitch in the film's own words, then the live demo and a short guide to it. */
export default function Landing({ onEnter }: { onEnter: () => void }) {
  const { checkoutDown, money } = useRevenue();
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
          <a href="#what">What it does</a>
          <a href="#guide">How to try it</a>
          <a href={REPO} target="_blank" rel="noreferrer">GitHub</a>
          <a className="film-btn small" href="#demo">Try the live demo</a>
        </nav>
      </header>

      <section className="film-hero">
        <div className="film-hud">
          <span>LUMEN COFFEE CO. · REVENUE</span>
          <span className={`film-state ${checkoutDown ? "down" : ""}`}>
            <i />
            {checkoutDown ? "CHECKOUT DOWN" : "TAKING PAYMENTS"}
          </span>
        </div>
        <div className="film-pulse">
          <Pulse alive={!checkoutDown} height={170} seconds={7} stroke={3.2} />
        </div>
        <p className="film-kicker">We put people on call for servers.</p>
        <h1>
          Nobody is on call for the <em>money.</em>
        </h1>
        <p className="film-sub">
          Flatline is an on-call engineer for your PayPal revenue. It notices when your checkout breaks, fixes it, and gets the lost sales back.
        </p>
        <div className="film-cta">
          <a className="film-btn" href="#demo">Try the live demo</a>
          {VIDEO ? (
            <a className="film-btn ghost" href={VIDEO} target="_blank" rel="noreferrer">Watch the film (2:41)</a>
          ) : null}
          <a className="film-btn ghost" href={REPO} target="_blank" rel="noreferrer">Read the code</a>
        </div>
        <p className="film-fine">The line above is live: it is this demo shop&apos;s checkout right now. Break it and it goes flat.</p>
      </section>

      <section className="film-money">
        <div>
          <span className="film-label">LOST TO INCIDENTS</span>
          <strong className="lost">{cash(money?.impact, money?.currency)}</strong>
          <span className="film-serif">{money?.counts.impact ?? 0} sales that failed or were refunded</span>
        </div>
        <div>
          <span className="film-label">ASKED BACK</span>
          <strong>{cash(money?.requested, money?.currency)}</strong>
          <span className="film-serif">{money?.counts.requested ?? 0} customers, each batch approved by a person</span>
        </div>
        <div>
          <span className="film-label">RECOVERED</span>
          <strong className="back">{cash(money?.recovered, money?.currency)}</strong>
          <span className="film-serif">in this demo so far{money?.simulated ? ", partly simulated and labelled" : ""}</span>
        </div>
      </section>

      <section id="what" className="film-section">
        <h2>
          Most tools stop at &ldquo;resolved&rdquo;. <em>Flatline goes after the money.</em>
        </h2>
        <p className="film-lede">
          A config change goes out on a Friday evening and checkout breaks. The servers are fine, every dashboard is green, and the shop finds out
          on Monday. Flatline finds out in seconds.
        </p>
        <div className="film-steps">
          {WHAT.map(([name, sub, text], i) => (
            <article key={name}>
              <span className="film-label">STEP {i + 1}</span>
              <h3>{name}</h3>
              <p className="film-serif">{sub}</p>
              <p>{text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="film-section">
        <h2>
          The agents can only ask. <em>Code decides.</em>
        </h2>
        <div className="film-tiers">
          {TIERS.map(([tier, sub, items]) => (
            <article key={tier} className={tier}>
              <span className="film-tier">{tier.toUpperCase()}</span>
              <p className="film-serif">{sub}</p>
              <ul>
                {items.map((it) => (
                  <li key={it}>{it}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <section id="demo" className="film-section">
        <span className="film-label">THE LIVE DEMO HAS TWO PARTS</span>
        <h2>
          Don&apos;t take our word for it. <em>Break the shop yourself.</em>
        </h2>
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
        <h2>
          Four steps, <em>start to finish.</em>
        </h2>
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
