import React, { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { getRelativePathFromParams } from '../../router/url';
import { useStore } from '../../state/store';
import { toAbsolutePath } from '../../utils/path';
import { Navbar } from '../navbar/Navbar';

export const ScanDetail: React.FC = () => {
  const params = useParams<{ '*': string }>();
  const relativePath = getRelativePathFromParams(params);
  const resultsDir = useStore((state) => state.resultsDir);

  // Convert relative path back to absolute path
  const absolutePath = resultsDir
    ? toAbsolutePath(relativePath, resultsDir)
    : relativePath;

  const setSelectedScan = useStore((state) => state.setSelectedScan);
  const selectedScan = useStore((state) => state.selectedScan);
  const api = useStore((state) => state.api);

  useEffect(() => {
    const fetchScans = async () => {
      const scansInfo = await api?.getScan(absolutePath);
      if (scansInfo) {
        setSelectedScan(scansInfo)
      }
    };
    void fetchScans();
  }, [absolutePath, api, setSelectedScan]);

  // TODO: Replace with actual scan data fetching from your store or API
  // For now, just display the scan location

  return (
    <>
      <Navbar />
      <div style={{ height: "100%", overflowY: "auto", padding: '16px' }}>
        {selectedScan ? (
          <pre>{JSON.stringify(selectedScan, null, 2)}</pre>
        ) : (
          <p>Loading scan details...</p>
        )}
      </div>
    </>
  );
};
