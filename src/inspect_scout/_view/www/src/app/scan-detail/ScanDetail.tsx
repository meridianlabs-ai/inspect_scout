import React from "react";
import { Link, useParams } from "react-router-dom";
import { scansRoute } from "../../router/url";

export const ScanDetail: React.FC = () => {
  const { scan_location } = useParams<{ scan_location: string }>();

  // TODO: Replace with actual scan data fetching from your store or API
  // For now, just display the scan location

  return (
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
                {scan_location}
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
                <code>{scan_location}</code>
              </p>

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
  );
};
