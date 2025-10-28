import { FC, useEffect } from 'react';
import { useStore } from '../../state/store';
import { Navbar } from '../navbar/Navbar';
import { ExtendedFindProvider } from '../../components/ExtendedFindContext';
import { ScansGrid } from './ScansGrid';

export const ScanList: FC = () => {
  const setScans = useStore((state) => state.setScans);
  const setResultsDir = useStore((state) => state.setResultsDir);
  const api = useStore((state) => state.api);
  const scans = useStore((state) => state.scans);

  useEffect(() => {
    const fetchScans = async () => {
      const scansInfo = await api?.getScans();
      if (scansInfo) {
        setResultsDir(scansInfo.results_dir);
        setScans(scansInfo.scans);
      }
    };
    void fetchScans();
  }, [api, setScans, setResultsDir]);

  return (
    <>
      <Navbar bordered={false} />
      <ExtendedFindProvider>
        {scans.length > 0 && <ScansGrid />}
      </ExtendedFindProvider>
    </>
  );
};
