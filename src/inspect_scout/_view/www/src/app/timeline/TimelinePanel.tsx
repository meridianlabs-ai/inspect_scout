import {
  VscodeOption,
  VscodeSingleSelect,
} from "@vscode-elements/react-elements";
import { FC, useEffect, useMemo, useState } from "react";

import { useEventNodes } from "../../components/transcript/hooks/useEventNodes";
import { TranscriptViewNodes } from "../../components/transcript/TranscriptViewNodes";
import { useDocumentTitle } from "../../hooks/useDocumentTitle";

import { computeRowLayouts } from "./swimlaneLayout";
import { SwimLanePanel } from "./SwimLanePanel";
import { timelineScenarios } from "./syntheticNodes";
import { collectRawEvents, getSelectedSpans } from "./timelineEventNodes";
import styles from "./TimelinePanel.module.css";
import { TimelinePills } from "./TimelinePills";
import { useTimeline } from "./useTimeline";

export const TimelinePanel: FC = () => {
  useDocumentTitle("Timeline");

  const [selectedIndex, setSelectedIndex] = useState(0);
  const scenario = timelineScenarios[selectedIndex];

  const timeline = scenario?.timeline;
  const state = useTimeline(timeline!);

  // Clear drill-down path on mount so reloads start at root
  useEffect(() => {
    state.navigateTo("");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const layouts = useMemo(
    () =>
      computeRowLayouts(
        state.rows,
        state.node.startTime,
        state.node.endTime,
        "children"
      ),
    [state.rows, state.node.startTime, state.node.endTime]
  );

  const atRoot = state.breadcrumbs.length <= 1;

  // Event list for the selected swimlane row
  const selectedSpans = useMemo(
    () => getSelectedSpans(state.rows, state.selected),
    [state.rows, state.selected]
  );
  const rawEvents = useMemo(
    () => collectRawEvents(selectedSpans),
    [selectedSpans]
  );
  const { eventNodes, defaultCollapsedIds } = useEventNodes(rawEvents, false);

  return (
    <div className={styles.container}>
      <div className={styles.headerRow}>
        <h2 className={styles.title}>Timeline</h2>
        <VscodeSingleSelect
          value={String(selectedIndex)}
          onChange={(e) => {
            const target = e.target as HTMLSelectElement;
            setSelectedIndex(Number(target.value));
            state.navigateTo("");
          }}
          className={styles.scenarioSelect}
        >
          {timelineScenarios.map((s, i) => (
            <VscodeOption key={i} value={String(i)}>
              {s.name}
            </VscodeOption>
          ))}
        </VscodeSingleSelect>
        <span className={styles.scenarioDescription}>
          {scenario?.description}
        </span>
      </div>
      <div className={styles.content}>
        <TimelinePills timelines={[]} activeIndex={0} onSelect={() => {}} />
        <SwimLanePanel
          layouts={layouts}
          selected={state.selected}
          node={state.node}
          onSelect={state.select}
          onDrillDown={state.drillDown}
          onBranchDrillDown={state.drillDown}
          onGoUp={state.goUp}
          minimap={{
            root: timeline!.root,
            current: state.node,
          }}
          breadcrumb={{
            breadcrumbs: state.breadcrumbs,
            atRoot,
            onGoUp: state.goUp,
            onNavigate: state.navigateTo,
          }}
        />
        {eventNodes.length > 0 && (
          <div className={styles.eventList}>
            <TranscriptViewNodes
              id="timeline-events"
              eventNodes={eventNodes}
              defaultCollapsedIds={defaultCollapsedIds}
            />
          </div>
        )}
      </div>
    </div>
  );
};
