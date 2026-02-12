import { FC } from "react";

import { CompactionEvent } from "../../types/api-types";
import { formatDateTime } from "../../utils/format";
import { MetaDataGrid } from "../content/MetaDataGrid";
import { ApplicationIcons } from "../icons";

import styles from "./CompactionEventView.module.css";
import { EventPanel } from "./event/EventPanel";
import { formatTitle } from "./event/utils";
import { EventNode } from "./types";

interface CompactionEventViewProps {
  eventNode: EventNode<CompactionEvent>;
  className?: string | string[];
}

/**
 * Renders the CompactionEventView component.
 */
export const CompactionEventView: FC<CompactionEventViewProps> = ({
  eventNode,
  className,
}) => {
  const event = eventNode.event;
  let data: Record<string, unknown> = {};
  if (event.tokens_before) {
    data["tokens_before"] = event.tokens_before;
  }
  if (event.tokens_after) {
    data["tokens_after"] = event.tokens_after;
  }
  data = { ...data, ...(event.metadata || {}) };

  const source = event.source && event.source !== "inspect" ? event.source : "";

  return (
    <EventPanel
      eventNodeId={eventNode.id}
      depth={eventNode.depth}
      title={formatTitle("Compaction" + source, undefined, event.working_start)}
      className={className}
      subTitle={formatDateTime(new Date(event.timestamp))}
      icon={ApplicationIcons.compaction}
    >
      <MetaDataGrid entries={data} className={styles.panel} />
    </EventPanel>
  );
};
