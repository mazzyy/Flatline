import { useEffect, useMemo, useState } from "react";
import { passcode, setInjectToken, setPasscode } from "./api";
import AuditPage from "./pages/Audit";
import ChaosPage from "./pages/Chaos";
import IncidentPage from "./pages/Incident";
import Overview from "./pages/Overview";
import PolicyPage from "./pages/Policy";
import Transactions from "./pages/Transactions";

type Page = "overview" | "incident" | "transactions" | "policy" | "audit" | "chaos";

function parseHash(): { page: Page; id?: string } {
  const raw = location.hash.replace(/^#\/?/, "") || "overview";
  const [page, id] = raw.split("/");
  if (page === "incident") return { page: "incident", id };
  if (["transactions", "policy", "audit", "chaos"].includes(page)) return { page: page as Page };
  return { page: "overview" };
}

export default function App() {
  const [authed, setAuthed] = useState(Boolean(passcode()));
  const [route, setRoute] = useState(parseHash);
  const [theme, setTheme] = useState<"light" | "dark" | "auto">("auto");
  const [flash, setFlash] = useState("");

  useEffect(() => {
    const onHash = () => setRoute(parseHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    if (theme === "auto") document.documentElement.removeAttribute("data-theme");
    else document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  useEffect(() => {
    if (!authed) return;
    const es = new EventSource("/api/stream");
    es.onmessage = () => setFlash("live");
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
        setFlash(name);
        window.dispatchEvent(new CustomEvent("warden-sse", { detail: name }));
      });
    }
    return () => es.close();
  }, [authed]);

  const page = useMemo(() => {
    if (route.page === "transactions") return <Transactions />;
    if (route.page === "policy") return <PolicyPage />;
    if (route.page === "audit") return <AuditPage />;
    if (route.page === "chaos") return <ChaosPage />;
    if (route.page === "incident") return <IncidentPage id={route.id || ""} />;
    return <Overview />;
  }, [route]);

  if (!authed) {
    return (
      <div className="card login">
        <h1>Warden for Payments</h1>
        <p className="muted">Shared demo passcode. Default is <code>demo-judge</code>.</p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const fd = new FormData(e.currentTarget);
            setPasscode(String(fd.get("pass") || ""));
            setInjectToken(String(fd.get("inject") || "change-me"));
            setAuthed(true);
          }}
        >
          <p><input name="pass" placeholder="passcode" defaultValue="demo-judge" /></p>
          <p><input name="inject" placeholder="inject token" defaultValue="change-me" /></p>
          <button type="submit">Enter</button>
        </form>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <aside>
        <div className="brand">Warden</div>
        <div className="muted">for Payments</div>
        <nav>
          <a className={route.page === "overview" ? "active" : ""} href="#/overview">Overview</a>
          <a className={route.page === "transactions" ? "active" : ""} href="#/transactions">Transactions</a>
          <a className={route.page === "policy" ? "active" : ""} href="#/policy">Policy</a>
          <a className={route.page === "audit" ? "active" : ""} href="#/audit">Audit</a>
          <a className={route.page === "chaos" ? "active" : ""} href="#/chaos">Chaos</a>
        </nav>
        <p className="muted">{flash ? `SSE: ${flash}` : "SSE idle"}</p>
        <div className="theme">
          <button className="secondary" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
            Theme: {theme}
          </button>
        </div>
      </aside>
      <main>{page}</main>
    </div>
  );
}
