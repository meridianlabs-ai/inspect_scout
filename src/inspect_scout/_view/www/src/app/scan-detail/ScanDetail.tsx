import React, { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { getRelativePathFromParams } from '../../router/url';
import { useStore } from '../../state/store';
import { Navbar } from '../navbar/Navbar';

export const ScanDetail: React.FC = () => {
  const params = useParams<{ '*': string }>();
  const relativePath = getRelativePathFromParams(params);
  const singleFileMode = useStore((state) => state.singleFileMode);
  
  const resultsDir = useStore((state) => state.resultsDir);
  const setResultsDir = useStore((state) => state.setResultsDir);

  const selectedScan = useStore((state) => state.selectedScan);
  const setSelectedScan = useStore((state) => state.setSelectedScan);
  
  const setScans = useStore((state) => state.setScans);
  const api = useStore((state) => state.api);

  useEffect(() => {
    const fetchScans = async () => {
      if (resultsDir === undefined) {
        const scansInfo = await api?.getScans();
        if (scansInfo) {
          setResultsDir(scansInfo.results_dir);
          setScans(scansInfo.scans);
        }
      }

      const scansInfo = await api?.getScan(relativePath);
      if (scansInfo) {
        setSelectedScan(scansInfo);
      }
    };
    void fetchScans();
  }, [resultsDir, relativePath, api, setSelectedScan, setResultsDir, setScans]);

  return (
    <>
      {singleFileMode || <Navbar />}
      <div style={{ height: '100%', overflowY: 'auto', padding: '16px' }}>
        {selectedScan ? (
          <pre>{JSON.stringify(selectedScan, null, 2)}</pre>
        ) : (
          <p>Loading scan details...</p>
        )}
      </div>
    </>
  );
};
