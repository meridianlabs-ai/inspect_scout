import { useMemo } from "react";
import { useStore } from "../../../state/store";

export const useSelectedScanner = () => {
    const selectedScanner = useStore((state) => state.selectedScanner);
    const selectedResults = useStore((state) => state.selectedResults);
    const defaultScanner = useMemo(() => {
        if (selectedResults) {
            const scanners = Object.keys(selectedResults.summary.scanners);
            return scanners.length > 0 ? scanners[0] : undefined;
        }
    }, [selectedResults])

    return selectedScanner ||defaultScanner;
}