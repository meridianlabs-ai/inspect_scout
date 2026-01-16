import clsx from "clsx";
import { FC, ReactNode, useRef } from "react";
import { Link } from "react-router-dom";

import { formatDateTime, formatTime } from "../../../utils/format";
import { parsePackageName } from "../../../utils/python";
import { MetaDataGrid } from "../../content/MetaDataGrid";
import { ApplicationIcons } from "../../icons";
import { PulsingDots } from "../../PulsingDots";
import { useCollapseTranscriptEvent } from "../hooks/useCollapseTranscriptEvent";
import { kSandboxSignalName } from "../transform/fixups";
import { EventNode } from "../types";

import styles from "./OutlineRow.module.css";

export interface OutlineRowProps {
  node: EventNode;
  collapseScope: string;
  running?: boolean;
  selected?: boolean;
  getEventUrl?: (eventId: string) => string | undefined;
}

export const OutlineRow: FC<OutlineRowProps> = ({
  node,
  collapseScope,
  running,
  selected,
  getEventUrl,
}) => {
  const [collapsed, setCollapsed] = useCollapseTranscriptEvent(
    collapseScope,
    node.id
  );
  const icon = iconForNode(node);
  const toggle = toggleIcon(node, collapsed);

  const ref = useRef(null);

  // Generate URL for deep linking to this event
  const eventUrl = getEventUrl?.(node.id);

  return (
    <>
      <div
        className={clsx(
          styles.eventRow,
          "text-size-smaller",
          selected ? styles.selected : ""
        )}
        style={{ paddingLeft: `${node.depth * 0.4}em` }}
        data-unsearchable={true}
      >
        <div
          className={clsx(styles.toggle)}
          onClick={() => {
            setCollapsed(!collapsed);
          }}
        >
          {toggle ? <i className={clsx(toggle)} /> : undefined}
        </div>
        <div className={clsx(styles.label)} data-depth={node.depth}>
          {icon ? <i className={clsx(icon, styles.icon)} /> : undefined}
          {eventUrl ? (
            <Link to={eventUrl} className={clsx(styles.eventLink)} ref={ref}>
              {parsePackageName(labelForNode(node)).module}
            </Link>
          ) : (
            <span ref={ref}>{parsePackageName(labelForNode(node)).module}</span>
          )}
          {running ? (
            <PulsingDots
              size="small"
              className={clsx(styles.progress)}
              subtle={false}
            />
          ) : undefined}
        </div>
      </div>
    </>
  );
};

const toggleIcon = (
  node: EventNode,
  collapsed: boolean
): string | undefined => {
  if (node.children.length > 0) {
    return collapsed
      ? ApplicationIcons.chevron.right
      : ApplicationIcons.chevron.down;
  }
};

const iconForNode = (node: EventNode): string | undefined => {
  switch (node.event.event) {
    case "sample_limit":
      return ApplicationIcons.limits.custom;

    case "score":
      return ApplicationIcons.scorer;

    case "error":
      return ApplicationIcons.error;
  }
};

const labelForNode = (node: EventNode): string => {
  if (node.event.event === "span_begin") {
    switch (node.event.type) {
      case "solver":
        return node.event.name;
      case "tool":
        return node.event.name;
      default: {
        if (node.event.name === kSandboxSignalName) {
          return "sandbox events";
        }
        return node.event.name;
      }
    }
  } else {
    switch (node.event.event) {
      case "subtask":
        return node.event.name;
      case "approval":
        switch (node.event.decision) {
          case "approve":
            return "approved";
          case "reject":
            return "rejected";
          case "escalate":
            return "escalated";
          case "modify":
            return "modified";
          case "terminate":
            return "terminated";
          default:
            return node.event.decision;
        }
      case "model":
        return `model${node.event.role ? ` (${node.event.role})` : ""}`;
      case "score":
        return "scoring";
      case "step":
        if (node.event.name === kSandboxSignalName) {
          return "sandbox events";
        }
        return node.event.name;

      default:
        return node.event.event;
    }
  }
};

export const summarizeNode = (node: EventNode): ReactNode => {
  let entries: Record<string, unknown> = {};
  switch (node.event.event) {
    case "sample_init":
      entries = {
        sample_id: node.event.sample.id,
        sandbox: node.event.sample.sandbox?.type,
        started: node.event.timestamp
          ? formatDateTime(new Date(node.event.timestamp))
          : undefined,
        working_start: node.event.working_start
          ? formatTime(node.event.working_start)
          : undefined,
      };
      break;

    case "sample_limit":
      entries = {
        type: node.event.type,
        message: node.event.message,
        limit: node.event.limit,
        started: node.event.timestamp
          ? formatDateTime(new Date(node.event.timestamp))
          : undefined,
        working_start: node.event.working_start
          ? formatTime(node.event.working_start)
          : undefined,
      };
      break;
    case "score":
      entries = {
        answer: node.event.score.answer,
        score: node.event.score.value,
        started: node.event.timestamp
          ? formatDateTime(new Date(node.event.timestamp))
          : undefined,
        working_start: node.event.working_start
          ? formatTime(node.event.working_start)
          : undefined,
      };
      break;
    case "span_begin":
      entries = {
        name: node.event.name,
        started: node.event.timestamp
          ? formatDateTime(new Date(node.event.timestamp))
          : undefined,
        working_start: node.event.working_start
          ? formatTime(node.event.working_start)
          : undefined,
      };
      break;
    default:
      entries = {
        started: node.event.timestamp
          ? formatDateTime(new Date(node.event.timestamp))
          : undefined,
        working_start: node.event.working_start
          ? formatTime(node.event.working_start)
          : undefined,
      };
  }

  return (
    <MetaDataGrid
      entries={entries}
      options={{ size: "mini" }}
      className={clsx(styles.popover, "text-size-smallest")}
    />
  );
};
