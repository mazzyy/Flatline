import { useEffect, useMemo, useState } from "react";
import { passcode, setInjectToken, setPasscode } from "./api";
import AuditPage from "./pages/Audit";
import ChaosPage from "./pages/Chaos";
import HowItWorks from "./pages/HowItWorks";
import IncidentPage from "./pages/Incident";
import Overview from "./pages/Overview";
import PolicyPage from "./pages/Policy";
import Transactions from "./pages/Transactions";

type Page = "overview" | "how" | "incident" | "transactions" | "policy" | "audit" | "chaos";

function parseHash(): { page: Page; id?: string } {
  const raw = location.hash.replace(/^#\/?/, "") || "overview";
  const [page, id] = raw.split("/");
  if (page === "incident") return { page: "incident", id };
  if (["how", "transactions", "policy", "audit", "chaos"].includes(page)) return { page: page as Page };
  return { page: "overview" };
}

const NAV: { page: Page; label: string }[] = [
  { page: "overview", label: "Overview" },
  { page: "how", label: "How it works" },
  { page: "transactions", label: "Transactions" },
  { page: "policy", label: "Policy" },
  { page: "audit", label: "Audit" },
  { page: "chaos", label: "Chaos" },
];

export default function App() {
  const [authed, setAuthed] = useState(Boolean(passcode()));
  const [route, setRoute] = useState(parseHash);
  const [live, setLive] = useState(false);
  const [lastEvent, setLastEvent] = useState("");

  useEffect(() => {
    const onHash = () => setRoute(parseHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    if (!authed) return;
    const es = new EventSource("/api/stream");
    es.onopen = () => setLive(true);
    es.onerror = () => setLive(false);
    es.onmessage = () => setLive(true);
    const evs = [
      "incident.created",
      "incident.updated",
      "step.added",
      "proposal.created",
      "proposal.updated",
      "event.ingested",
    ];
    for (const name of evs) {
      es.addEventListener(name, () => {
        setLive(true);
        setLastEvent(name);
        window.dispatchEvent(new CustomEvent("warden-sse", { detail: name }));
      });
    }
    return () => es.close();
  }, [authed]);

  const page = useMemo(() => {
    if (route.page === "how") return <HowItWorks />;
    if (route.page === "transactions") return <Transactions />;
    if (route.page === "policy") return <PolicyPage />;
    if (route.page === "audit") return <AuditPage />;
    if (route.page === "chaos") return <ChaosPage />;
    if (route.page === "incident") return <IncidentPage id={route.id || ""} />;
    return <Overview />;
  }, [route]);

  if (!authed) {
    return (
      <div className="login-wrap">
        <div className="card login">
          <div className="brand">
            <span className="brand-mark" />
            Flatline <small>for Payments</small>
          </div>
          <h1>Log in to the demo</h1>
          <p className="muted">An on-call agent for a merchant&apos;s PayPal revenue.</p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const fd = new FormData(e.currentTarget);
              setPasscode(String(fd.get("pass") || ""));
              setInjectToken(String(fd.get("inject") || "change-me"));
              setAuthed(true);
            }}
          >
            <div className="field">
              <label htmlFor="pass">Shared passcode</label>
              <input id="pass" name="pass" placeholder="passcode" defaultValue="demo-judge" />
            </div>
            <div className="field">
              <label htmlFor="inject">Chaos / inject token</label>
              <input id="inject" name="inject" placeholder="inject token" defaultValue="change-me" />
            </div>
            <button type="submit">Log In</button>
          </form>
          <p className="foot muted">
            Sandbox and mock data only. There is no live PayPal path.
          </p>
        </div>
      </div>
    );
  }

  return (
    <>
      <header className="pp-header">
        <div className="pp-header-inner">
          <a className="brand" href="#/overview">
            <span className="brand-mark" />
            Flatline <small>for Payments</small>
          </a>
          <nav className="pp-nav">
            {NAV.map((n) => (
              <a key={n.page} className={route.page === n.page ? "active" : ""} href={`#/${n.page}`}>
                {n.label}
              </a>
            ))}
          </nav>
          <div className="pp-header-right">
            <span className={`live ${live ? "on" : ""}`} title={lastEvent || "waiting for events"}>
              {live ? (lastEvent ? `Live · ${lastEvent}` : "Live") : "Connecting"}
            </span>
            <button
              className="secondary small"
              onClick={() => {
                sessionStorage.clear();
                setAuthed(false);
              }}
            >
              Log Out
            </button>
          </div>
        </div>
      </header>
      <main className="pp-main">{page}</main>
    </>
  );
}
