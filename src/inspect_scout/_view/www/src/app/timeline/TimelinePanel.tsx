import {
  VscodeOption,
  VscodeSingleSelect,
} from "@vscode-elements/react-elements";
import clsx from "clsx";
import { FC, useEffect, useMemo, useState } from "react";

import { ApplicationIcons } from "../../components/icons";
import { useEventNodes } from "../../components/transcript/hooks/useEventNodes";
import { TranscriptOutline } from "../../components/transcript/outline/TranscriptOutline";
import { TranscriptViewNodes } from "../../components/transcript/TranscriptViewNodes";
import { useDocumentTitle } from "../../hooks/useDocumentTitle";
import { useProperty } from "../../state/hooks/useProperty";

import { TimelinePills } from "./components/TimelinePills";
import { TimelineSwimLanes } from "./components/TimelineSwimLanes";
import { useTimeline } from "./hooks/useTimeline";
import { timelineScenarios } from "./syntheticNodes";
import {
  collectRawEvents,
  computeMinimapSelection,
  getSelectedSpans,
} from "./timelineEventNodes";
import styles from "./TimelinePanel.module.css";
import type { MarkerDepth } from "./utils/markers";
import { computeRowLayouts } from "./utils/swimlaneLayout";

export const TimelinePanel: FC = () => {
  useDocumentTitle("Timeline");

  const [selectedIndex, setSelectedIndex] = useState(0);
  const [markerDepth, setMarkerDepth] = useState<MarkerDepth>("direct");
  const [outlineCollapsed, setOutlineCollapsed] = useProperty<boolean>(
    "timeline",
    "outlineCollapsed",
    { defaultValue: true, cleanup: false }
  );
  const isOutlineCollapsed = !!outlineCollapsed;
  const scenario = timelineScenarios[selectedIndex];
  // Guaranteed to be defined: selectedIndex is initialized to 0 and the
  // select only offers valid indices, but we fall back to [0] defensively.
  const timeline = scenario?.timeline ?? timelineScenarios[0]!.timeline;
  const state = useTimeline(timeline);

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
        markerDepth
      ),
    [state.rows, state.node.startTime, state.node.endTime, markerDepth]
  );

  const atRoot = state.breadcrumbs.length <= 1;

  // Resolved spans for the selected swimlane row (all spans, for event display)
  const selectedSpans = useMemo(
    () => getSelectedSpans(state.rows, state.selected),
    [state.rows, state.selected]
  );

  const minimapSelection = useMemo(
    () => computeMinimapSelection(state.rows, state.selected),
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
            // Cast required: @vscode-elements/react-elements types onChange as Event
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
        <VscodeSingleSelect
          value={markerDepth}
          onChange={(e) => {
            // Cast required: @vscode-elements/react-elements types onChange as Event
            const target = e.target as HTMLSelectElement;
            setMarkerDepth(target.value as MarkerDepth);
          }}
          className={styles.markerDepthSelect}
        >
          <VscodeOption value="direct">Markers: direct</VscodeOption>
          <VscodeOption value="children">Markers: children</VscodeOption>
          <VscodeOption value="recursive">Markers: recursive</VscodeOption>
        </VscodeSingleSelect>
        <span className={styles.scenarioDescription}>
          {scenario?.description}
        </span>
      </div>
      <div className={styles.content}>
        <TimelinePills timelines={[]} activeIndex={0} onSelect={() => {}} />
        <TimelineSwimLanes
          layouts={layouts}
          selected={state.selected}
          node={state.node}
          onSelect={state.select}
          onDrillDown={state.drillDown}
          onGoUp={state.goUp}
          minimap={{
            root: timeline.root,
            selection: minimapSelection,
          }}
          breadcrumb={{
            breadcrumbs: state.breadcrumbs,
            atRoot,
            onGoUp: state.goUp,
            onNavigate: state.navigateTo,
            selected: state.selected,
          }}
        />
        {eventNodes.length > 0 ? (
          <div
            className={clsx(
              styles.eventsContainer,
              isOutlineCollapsed && styles.outlineCollapsed
            )}
          >
            <div className={styles.outlinePane}>
              {!isOutlineCollapsed && (
                <TranscriptOutline
                  eventNodes={eventNodes}
                  defaultCollapsedIds={defaultCollapsedIds}
                  className={styles.outline}
                />
              )}
              <div
                className={styles.outlineToggle}
                onClick={() => setOutlineCollapsed(!isOutlineCollapsed)}
              >
                <i className={ApplicationIcons.sidebar} />
              </div>
            </div>
            <div className={styles.eventsSeparator} />
            <div className={styles.eventList}>
              <TranscriptViewNodes
                id="timeline-events"
                eventNodes={eventNodes}
                defaultCollapsedIds={defaultCollapsedIds}
              />
            </div>
          </div>
        ) : (
          <div className={styles.emptyEvents}>
            Select a swimlane row to view events
          </div>
        )}
      </div>
    </div>
  );
};
