import React from "react";
import { Link, useParams } from "react-router-dom";
import { scansRoute, getRelativePathFromParams } from "../../router/url";
import { useStore } from "../../state/store";
import { toAbsolutePath } from "../../utils/path";
import { Navbar } from "../navbar/Navbar";

export const ScanDetail: React.FC = () => {
  const params = useParams<{ "*": string }>();
  const relativePath = getRelativePathFromParams(params);
  const resultsDir = useStore((state) => state.resultsDir);

  // Convert relative path back to absolute path
  const absolutePath = resultsDir ? toAbsolutePath(relativePath, resultsDir) : relativePath;

  // TODO: Replace with actual scan data fetching from your store or API
  // For now, just display the scan location

  return (
    <>
    <Navbar/>
    <div className="container mt-5">
      <div className="row">
        <div className="col">
          <nav aria-label="breadcrumb">
            <ol className="breadcrumb">
              <li className="breadcrumb-item">
                <Link to={scansRoute()}>
                  <i className="bi bi-arrow-left me-2"></i>
                  Scans
                </Link>
              </li>
              <li className="breadcrumb-item active" aria-current="page">
                {relativePath}
              </li>
            </ol>
          </nav>

          <h1 className="mb-4">
            <i className="bi bi-file-earmark-text me-2"></i>
            Scan Detail
          </h1>

          <div className="card">
            <div className="card-body">
              <h5 className="card-title">Scan Location</h5>
              <p className="card-text">
                <code>{relativePath}</code>
              </p>
              <small className="text-muted">Full path: {absolutePath}</small>

              <hr />

              <div className="alert alert-info" role="alert">
                <i className="bi bi-info-circle me-2"></i>
                TODO: Load and display scan details for this location
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    </>
  );
};
