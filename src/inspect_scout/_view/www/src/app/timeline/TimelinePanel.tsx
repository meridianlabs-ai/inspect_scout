import {
  VscodeOption,
  VscodeSingleSelect,
} from "@vscode-elements/react-elements";
import { FC, useEffect, useMemo, useState } from "react";

import { useEventNodes } from "../../components/transcript/hooks/useEventNodes";
import { TranscriptOutline } from "../../components/transcript/outline/TranscriptOutline";
import { TranscriptViewNodes } from "../../components/transcript/TranscriptViewNodes";
import { useDocumentTitle } from "../../hooks/useDocumentTitle";

import { computeRowLayouts } from "./swimlaneLayout";
import { SwimLanePanel } from "./SwimLanePanel";
import { isSingleSpan, isParallelSpan } from "./swimlaneRows";
import { timelineScenarios } from "./syntheticNodes";
import { collectRawEvents, getSelectedSpans } from "./timelineEventNodes";
import type { MinimapSelection } from "./TimelineMinimap";
import styles from "./TimelinePanel.module.css";
import { TimelinePills } from "./TimelinePills";
import { parsePathSegment, useTimeline } from "./useTimeline";

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

  // Resolved spans for the selected swimlane row (all spans, for event display)
  const selectedSpans = useMemo(
    () => getSelectedSpans(state.rows, state.selected),
    [state.rows, state.selected]
  );

  // Minimap selection — resolve the single visually-highlighted span.
  // For multi-span rows (iterative), only the specific span is highlighted,
  // not the whole row envelope.
  const minimapSelection = useMemo((): MinimapSelection | undefined => {
    if (!state.selected) return undefined;
    const { name, spanIndex } = parsePathSegment(state.selected);
    const row = state.rows.find(
      (r) => r.name.toLowerCase() === name.toLowerCase()
    );
    if (!row) return undefined;

    // Resolve the specific span matching the visual selection
    const targetIndex = (spanIndex ?? 1) - 1; // 0-indexed, default to first
    for (const rowSpan of row.spans) {
      if (isSingleSpan(rowSpan)) {
        // For iterative rows, each SingleSpan corresponds to one index
        const singleIndex = row.spans.indexOf(rowSpan);
        if (singleIndex === targetIndex || row.spans.length === 1) {
          const agent = rowSpan.agent;
          return {
            startTime: agent.startTime,
            endTime: agent.endTime,
            totalTokens: agent.totalTokens,
          };
        }
      } else if (isParallelSpan(rowSpan)) {
        if (spanIndex !== null) {
          const agent = rowSpan.agents[spanIndex - 1];
          if (agent) {
            return {
              startTime: agent.startTime,
              endTime: agent.endTime,
              totalTokens: agent.totalTokens,
            };
          }
        }
        // No index → envelope of all parallel agents
        const agents = rowSpan.agents;
        const first = agents[0]!;
        let start = first.startTime;
        let end = first.endTime;
        let tokens = first.totalTokens;
        for (let i = 1; i < agents.length; i++) {
          const a = agents[i]!;
          if (a.startTime < start) start = a.startTime;
          if (a.endTime > end) end = a.endTime;
          tokens += a.totalTokens;
        }
        return { startTime: start, endTime: end, totalTokens: tokens };
      }
    }
    return undefined;
  }, [state.selected, state.rows]);

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
            selection: minimapSelection,
          }}
          breadcrumb={{
            breadcrumbs: state.breadcrumbs,
            atRoot,
            onGoUp: state.goUp,
            onNavigate: state.navigateTo,
          }}
        />
        {eventNodes.length > 0 && (
          <div className={styles.eventsContainer}>
            <TranscriptOutline
              eventNodes={eventNodes}
              defaultCollapsedIds={defaultCollapsedIds}
              className={styles.outline}
            />
            <div className={styles.eventsSeparator} />
            <div className={styles.eventList}>
              <TranscriptViewNodes
                id="timeline-events"
                eventNodes={eventNodes}
                defaultCollapsedIds={defaultCollapsedIds}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
