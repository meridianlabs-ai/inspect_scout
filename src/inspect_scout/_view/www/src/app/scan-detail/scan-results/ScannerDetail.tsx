import { FC, useMemo } from "react";
import { fromArrow } from "arquero";
import { AgGridReact } from "ag-grid-react";
import type { ColDef } from "ag-grid-community";

import { IPCDataframe } from "../../../types";

interface ScannerDetailProps {
  scanner: IPCDataframe;
}

export const ScannerDetail: FC<ScannerDetailProps> = ({ scanner }) => {
  const { columnDefs, rowData } = useMemo(() => {
    // Decode base64 string to Uint8Array
    const binaryString = atob(scanner.data);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }

    // Load Arrow data using Arquero
    const table = fromArrow(bytes.buffer);

    // Create column definitions for ag-grid
    const columnDefs: ColDef[] = scanner.column_names.map((name) => ({
      field: name,
      headerName: name,
      sortable: true,
      filter: true,
      resizable: true,
    }));

    // Convert table to array of objects for ag-grid
    const rowData = table.objects();

    return { columnDefs, rowData };
  }, [scanner]);

  return (
    <div style={{ height: "100%", width: "100%" }}>
      <div
        className="ag-theme-balham"
        style={{ height: "100%", width: "100%" }}
      >
        <AgGridReact
          columnDefs={columnDefs}
          rowData={rowData}
          defaultColDef={{
            flex: 1,
            minWidth: 100,
          }}
        />
      </div>
    </div>
  );
};
