import clsx from "clsx";
import { FC, Fragment } from "react";

import { ApplicationIcons } from "../../app/appearance/icons";
import { ScoreEditEvent } from "../../types/api-types";
import { formatDateTime } from "../../utils/format";
import { RecordTree } from "../content/RecordTree";
import { RenderedText } from "../content/RenderedText";

import { EventPanel } from "./event/EventPanel";
import styles from "./ScoreEditEventView.module.css";
import { renderScore } from "./ScoreEventView";
import { EventNode } from "./types";

interface ScoreEditEventViewProps {
  eventNode: EventNode<ScoreEditEvent>;
  className?: string | string[];
}
const kUnchangedSentinel = "UNCHANGED";

/**
 * Renders the ScoreEventView component.
 */
export const ScoreEditEventView: FC<ScoreEditEventViewProps> = ({
  eventNode,
  className,
}) => {
  const event = eventNode.event;

  const subtitle = event.edit.provenance
    ? `[${event.edit.provenance.timestamp ? formatDateTime(new Date(event.edit.provenance.timestamp)) : undefined}] ${event.edit.provenance.author}: ${event.edit.provenance.reason || ""}`
    : undefined;

  return (
    <EventPanel
      eventNodeId={eventNode.id}
      depth={eventNode.depth}
      title={"Edit Score"}
      className={clsx(className, "text-size-small")}
      subTitle={subtitle}
      collapsibleContent={true}
      icon={ApplicationIcons.edit}
    >
      <div data-name="Summary">
        <div
          className={clsx(
            "text-style-label",
            "text-style-secondary",
            styles.section
          )}
        >
          Updated Values
        </div>
        <div className={clsx(styles.container)}>
          {event.edit.value ? (
            <Fragment>
              <div className={clsx(styles.separator)}></div>
              <div className={"text-style-label"}>Value</div>
              <div>{renderScore(event.edit.value)}</div>
            </Fragment>
          ) : (
            ""
          )}

          <div className={clsx(styles.separator)}></div>
          <div className={"text-style-label"}>Answer</div>
          <div className={clsx(styles.wrappingContent)}>
            {event.edit.answer === kUnchangedSentinel ? (
              <pre className={clsx(styles.unchanged)}>[unchanged]</pre>
            ) : (
              <RenderedText markdown={event.edit.answer || ""} />
            )}
          </div>

          <div className={clsx(styles.separator)}></div>
          <div className={"text-style-label"}>Explanation</div>
          <div className={clsx(styles.wrappingContent)}>
            <RenderedText markdown={event.edit.explanation || ""} />
          </div>
        </div>

        {event.edit.provenance ? (
          <div className={clsx(styles.container)}>
            <div
              className={clsx(
                "text-style-label",
                "text-style-secondary",
                styles.section
              )}
            >
              Provenance
            </div>
            <div className={clsx(styles.spacer)}></div>

            <div className={clsx(styles.separator)}></div>
            <div className={"text-style-label"}>Author</div>
            <div className={clsx(styles.wrappingContent)}>
              <RenderedText markdown={event.edit.provenance.author} />
            </div>

            <div className={clsx(styles.separator)}></div>
            <div className={"text-style-label"}>Reason</div>
            <div className={clsx(styles.wrappingContent)}>
              <RenderedText markdown={event.edit.provenance.reason || ""} />
            </div>

            <div className={clsx(styles.separator)}></div>
            <div className={"text-style-label"}>Time</div>
            <div className={clsx(styles.wrappingContent)}>
              <RenderedText
                markdown={
                  event.edit.provenance.timestamp
                    ? formatDateTime(new Date(event.edit.provenance.timestamp))
                    : ""
                }
              />
            </div>
          </div>
        ) : (
          ""
        )}

        {event.edit.metadata && event.edit.metadata !== kUnchangedSentinel ? (
          <div data-name="Metadata">
            <RecordTree
              id={`${eventNode.id}-score-metadata`}
              record={event.edit.metadata || {}}
              className={styles.metadataTree}
              defaultExpandLevel={0}
            />
          </div>
        ) : undefined}
      </div>
    </EventPanel>
  );
};
