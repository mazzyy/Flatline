import { useEffect, useState } from "react";
import { get } from "./api";

export type Money = {
  impact: string;
  requested: string;
  recovered: string;
  outstanding: string;
  currency: string;
  simulated: boolean;
  counts: { impact: number; requested: number; recovered: number };
};
type IncidentRow = { playbook: string; status: string };

/** What the monitor strip and the landing page show: is checkout taking money, and the recovery totals. */
export function useRevenue(): { checkoutDown: boolean; open: number; money: Money | null } {
  const [state, setState] = useState<{ checkoutDown: boolean; open: number; money: Money | null }>({ checkoutDown: false, open: 0, money: null });
  useEffect(() => {
    let stop = false;
    const refresh = async () => {
      try {
        const [incidents, money] = await Promise.all([get<{ items: IncidentRow[] }>("/api/incidents"), get<Money>("/api/money")]);
        if (stop) return;
        // Once the fix is in and the verifier is watching, checkout is taking payments again.
        const live = incidents.items.filter((i) => !["resolved", "verifying"].includes(i.status));
        setState({ checkoutDown: live.some((i) => i.playbook === "checkout_failure_spike"), open: live.length, money });
      } catch {
        /* keep the last state */
      }
    };
    void refresh();
    const on = () => void refresh();
    window.addEventListener("flatline-sse", on);
    const timer = setInterval(() => void refresh(), 4000);
    return () => {
      stop = true;
      window.removeEventListener("flatline-sse", on);
      clearInterval(timer);
    };
  }, []);
  return state;
}

export function cash(value: string | undefined, currency = "USD"): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 0 }).format(Number(value || 0));
}
