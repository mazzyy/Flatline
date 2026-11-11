import Pulse from "./Pulse";
import { useRevenue } from "../useRevenue";

/** The strip from the film, above every page: the shop's pulse and whether it is taking payments. */
export default function Monitor() {
  const { checkoutDown, open } = useRevenue();
  return (
    <div className={`monitor ${checkoutDown ? "down" : ""}`}>
      <div className="monitor-inner">
        <span className="monitor-shop">LUMEN COFFEE CO. · REVENUE</span>
        <span className="monitor-state">
          <i />
          {checkoutDown ? "CHECKOUT DOWN" : "TAKING PAYMENTS"}
        </span>
        <div className="monitor-pulse">
          <Pulse alive={!checkoutDown} height={34} seconds={6} stroke={1.8} />
        </div>
        <span className="monitor-note">{open ? `${open} incident${open === 1 ? "" : "s"} open` : "all quiet"}</span>
      </div>
    </div>
  );
}
