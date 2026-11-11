import { useEffect, useState } from "react";
import { get } from "./api";

type Site = { shop_url: string; paypal_environment: string; llm_mode: string };

/** Where the demo shop lives: next to the dashboard when hosted as one container, else on port 3000. */
export function useSite(): { shopUrl: string; sandbox: boolean } {
  const local = `${location.protocol}//${location.hostname}:3000`;
  const [site, setSite] = useState<{ shopUrl: string; sandbox: boolean }>({ shopUrl: local, sandbox: false });
  useEffect(() => {
    get<Site>("/api/site")
      .then((s) => setSite({ shopUrl: s.shop_url || local, sandbox: s.paypal_environment === "SANDBOX" }))
      .catch(() => undefined);
  }, [local]);
  return site;
}
