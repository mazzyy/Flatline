import { useMemo } from "react";
import { AgGridReact } from "ag-grid-react";
import type { ColDef, IDatasource, IGetRowsParams } from "ag-grid-community";

type Row = {
  id: string;
  created_at: string;
  actor: string;
  action: string;
  incident_id: string | null;
};

export default function AuditPage() {
  const columnDefs = useMemo<ColDef<Row>[]>(
    () => [
      { field: "created_at", headerName: "When", minWidth: 200, sortable: true },
      { field: "actor", headerName: "Actor", width: 160 },
      { field: "action", headerName: "Action", minWidth: 200 },
      { field: "incident_id", headerName: "Incident", minWidth: 240 },
    ],
    [],
  );
  const datasource = useMemo<IDatasource>(
    () => ({
      getRows: (params: IGetRowsParams) => {
        const qs = new URLSearchParams({
          start_row: String(params.startRow ?? 0),
          end_row: String(params.endRow ?? 100),
        });
        fetch(`/api/audit?${qs}`)
          .then((r) => r.json())
          .then((body: { rows: Row[]; lastRow: number }) => params.successCallback(body.rows, body.lastRow))
          .catch(() => params.failCallback());
      },
    }),
    [],
  );
  return (
    <div>
      <h1>Audit log</h1>
      <div className="grid-wrap ag-theme-quartz">
        <AgGridReact<Row> columnDefs={columnDefs} rowModelType="infinite" datasource={datasource} cacheBlockSize={50} />
      </div>
    </div>
  );
}
