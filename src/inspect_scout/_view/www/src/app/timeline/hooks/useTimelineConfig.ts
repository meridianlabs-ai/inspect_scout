/**
 * Persistent configuration for timeline options (markers, agents).
 *
 * Each setting is stored via `useProperty` under the "timeline" id namespace
 * with `cleanup: false` so values survive unmount and persist across sessions.
 */

import { useCallback, useMemo } from "react";

import { useProperty } from "../../../state/hooks/useProperty";
import type { MarkerConfig, MarkerDepth, MarkerKind } from "../utils/markers";
import { defaultMarkerConfig } from "../utils/markers";

import type { TimelineOptions } from "./useTimeline";

// =============================================================================
// Types
// =============================================================================

export interface UseTimelineConfigResult {
  /** Resolved MarkerConfig for the timeline pipeline. */
  markerConfig: MarkerConfig;
  /** Resolved TimelineOptions for the timeline pipeline. */
  agentConfig: TimelineOptions;

  /** Current marker kinds selection. */
  markerKinds: MarkerKind[];
  /** Current marker depth selection. */
  markerDepth: MarkerDepth;
  /** Whether utility agents are shown. */
  includeUtility: boolean;

  setMarkerKinds: (kinds: MarkerKind[]) => void;
  setMarkerDepth: (depth: MarkerDepth) => void;
  setIncludeUtility: (include: boolean) => void;
  toggleMarkerKind: (kind: MarkerKind) => void;
  resetToDefaults: () => void;
  /** True when all settings match their defaults. */
  isDefault: boolean;
}

// =============================================================================
// Defaults
// =============================================================================

const kDefaultMarkerKinds = defaultMarkerConfig.kinds;
const kDefaultMarkerDepth = defaultMarkerConfig.depth;
const kDefaultIncludeUtility = false;

function arraysEqual<T>(a: T[], b: T[]): boolean {
  if (a.length !== b.length) return false;
  const sorted1 = [...a].sort();
  const sorted2 = [...b].sort();
  return sorted1.every((v, i) => v === sorted2[i]);
}

// =============================================================================
// Hook
// =============================================================================

export function useTimelineConfig(): UseTimelineConfigResult {
  const [storedKinds, setStoredKinds] = useProperty<MarkerKind[]>(
    "timeline",
    "markerKinds",
    { cleanup: false }
  );
  const [storedDepth, setStoredDepth] = useProperty<MarkerDepth>(
    "timeline",
    "markerDepth",
    { cleanup: false }
  );
  const [storedUtility, setStoredUtility] = useProperty<boolean>(
    "timeline",
    "includeUtility",
    { cleanup: false }
  );

  const markerKinds = storedKinds ?? kDefaultMarkerKinds;
  const markerDepth = storedDepth ?? kDefaultMarkerDepth;
  const includeUtility = storedUtility ?? kDefaultIncludeUtility;

  const markerConfig: MarkerConfig = useMemo(
    () => ({ kinds: markerKinds, depth: markerDepth }),
    [markerKinds, markerDepth]
  );

  const agentConfig: TimelineOptions = useMemo(
    () => ({ includeUtility }),
    [includeUtility]
  );

  const isDefault =
    arraysEqual(markerKinds, kDefaultMarkerKinds) &&
    markerDepth === kDefaultMarkerDepth &&
    includeUtility === kDefaultIncludeUtility;

  const toggleMarkerKind = useCallback(
    (kind: MarkerKind) => {
      const current = storedKinds ?? kDefaultMarkerKinds;
      const next = current.includes(kind)
        ? current.filter((k) => k !== kind)
        : [...current, kind];
      setStoredKinds(next);
    },
    [storedKinds, setStoredKinds]
  );

  const resetToDefaults = useCallback(() => {
    setStoredKinds(kDefaultMarkerKinds);
    setStoredDepth(kDefaultMarkerDepth);
    setStoredUtility(kDefaultIncludeUtility);
  }, [setStoredKinds, setStoredDepth, setStoredUtility]);

  return {
    markerConfig,
    agentConfig,
    markerKinds,
    markerDepth,
    includeUtility,
    setMarkerKinds: setStoredKinds,
    setMarkerDepth: setStoredDepth,
    setIncludeUtility: setStoredUtility,
    toggleMarkerKind,
    resetToDefaults,
    isDefault,
  };
}
