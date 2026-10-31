import { useMemo } from "react";
import { AgGridReact } from "ag-grid-react";
import type { ColDef, ColGroupDef, ICellRendererParams, IDatasource, IGetRowsParams } from "ag-grid-community";

type EventRow = {
  id: string;
  occurred_at: string;
  event_type: string;
  source: string;
  amount: string | null;
  currency: string | null;
  product_id: string | null;
  buyer_ref: string | null;
  error_code: string | null;
  synthetic: boolean;
};

function SimulatedBadge(props: ICellRendererParams<EventRow>) {
  if (!props.data?.synthetic) return null;
  return <span className="badge simulated">simulated</span>;
}

export default function Transactions() {
  const columnDefs = useMemo<(ColDef<EventRow> | ColGroupDef<EventRow>)[]>(
    () => [
      {
        headerName: "When",
        children: [
          { field: "occurred_at", headerName: "Occurred", sortable: true, minWidth: 200 },
          { field: "source", headerName: "Source", sortable: true, width: 150 },
        ],
      },
      {
        headerName: "What",
        children: [
          { field: "event_type", headerName: "Type", sortable: true, minWidth: 240 },
          { field: "error_code", headerName: "Error", width: 180 },
          {
            field: "synthetic",
            headerName: "Simulated",
            width: 130,
            cellRenderer: SimulatedBadge,
          },
        ],
      },
      {
        headerName: "Money",
        children: [
          { field: "amount", headerName: "Amount", sortable: true, width: 110 },
          { field: "currency", headerName: "CCY", width: 90 },
          { field: "product_id", headerName: "Product", minWidth: 160 },
          { field: "buyer_ref", headerName: "Buyer", width: 140 },
        ],
      },
    ],
    [],
  );

  const datasource = useMemo<IDatasource>(
    () => ({
      getRows: (params: IGetRowsParams) => {
        const sort = params.sortModel?.[0];
        const filter = params.filterModel?.event_type?.filter;
        const qs = new URLSearchParams({
          start_row: String(params.startRow ?? 0),
          end_row: String(params.endRow ?? 100),
          sort_field: sort?.colId || "occurred_at",
          sort_dir: sort?.sort || "desc",
        });
        if (filter) qs.set("filter_event_type", String(filter));
        const qf = (document.getElementById("qf") as HTMLInputElement | null)?.value;
        if (qf) qs.set("quick_filter", qf);
        fetch(`/api/events?${qs}`)
          .then((r) => r.json())
          .then((body: { rows: EventRow[]; lastRow: number }) => {
            params.successCallback(body.rows, body.lastRow);
          })
          .catch(() => params.failCallback());
      },
    }),
    [],
  );

  return (
    <div>
      <h1>Transactions</h1>
      <p className="lede">Every webhook and checkout event, sorted and filtered on the server. Simulated rows are labeled.</p>
      <div className="toolbar">
        <input id="qf" placeholder="Search type, order, product, buyer or error — press Enter" onKeyDown={(e) => {
          if (e.key === "Enter") {
            const api = (window as unknown as { __eventsGrid?: { purgeInfiniteCache: () => void } }).__eventsGrid;
            api?.purgeInfiniteCache();
          }
        }} />
      </div>
      <div className="grid-wrap ag-theme-quartz">
        <AgGridReact<EventRow>
          columnDefs={columnDefs}
          rowModelType="infinite"
          datasource={datasource}
          cacheBlockSize={50}
          maxBlocksInCache={8}
          onGridReady={(e) => {
            (window as unknown as { __eventsGrid?: unknown }).__eventsGrid = e.api;
          }}
        />
      </div>
    </div>
  );
}
