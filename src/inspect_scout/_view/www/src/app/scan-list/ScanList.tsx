import { FC, useEffect } from 'react';
import { useStore } from '../../store/store';
import { Link } from 'react-router-dom';

export const ScanList: FC = () => {
  const scans = useStore((state) => state.scans);
  const setScans = useStore((state) => state.setScans);
  const api = useStore((state) => state.api);

  useEffect(() => {
    const fetchScans = async () => {
      const scans = await api?.getScans();
      if (scans) {
        setScans(scans);
      }
    };
    void fetchScans();
  }, [api, setScans]);


  return (
    <div className="container mt-5">
      <div className="row">
        <div className="col">
          <h1 className="mb-4">
            <i className="bi bi-search me-2"></i>
            Scans
          </h1>

          <div className="list-group">
            {scans.map((scan) => (
              <Link
                key={scan.location}
                to={`/scan/${encodeURIComponent(scan.location)}`}
                className="list-group-item list-group-item-action"
              >
                <div className="d-flex w-100 justify-content-between">
                  <h5 className="mb-1">
                    <i className="bi bi-file-earmark-text me-2"></i>
                    {scan.location || 'Unnamed Scan'}
                  </h5>
                </div>
                <p className="mb-1">
                  <code>{scan.location}</code>
                </p>
              </Link>
            ))}
          </div>

          {scans.length === 0 && (
            <div className="alert alert-info" role="alert">
              <i className="bi bi-info-circle me-2"></i>
              No scans available.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
