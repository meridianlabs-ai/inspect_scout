// @ts-check
import clsx from "clsx";
import { FC, ReactNode } from "react";

import { ApplicationIcons } from "../app/appearance/icons";
import { ChatView } from "../chat/ChatView";
import { MetaDataGrid } from "../components/content/MetaDataGrid";
import { ChatMessage, SampleInitEvent } from "../types/api-types";
import { formatDateTime } from "../utils/format";
import { toArray } from "../utils/type";

import { EventPanel } from "./event/EventPanel";
import { EventSection } from "./event/EventSection";
import styles from "./SampleInitEventView.module.css";
import { EventNode } from "./types";

interface SampleInitEventViewProps {
  eventNode: EventNode<SampleInitEvent>;
  className?: string | string[];
}

/**
 * Renders the SampleInitEventView component.
 */
export const SampleInitEventView: FC<SampleInitEventViewProps> = ({
  eventNode,
  className,
}) => {
  const event = eventNode.event;
  const stateObj = event.state as Record<string, unknown>;

  const sections: ReactNode[] = [];

  if (event.sample.files && Object.keys(event.sample.files).length > 0) {
    sections.push(
      <EventSection title="Files" key={`event-${eventNode.id}`}>
        {Object.keys(event.sample.files).map((file) => {
          return (
            <pre key={`sample-init-file-${file}`} className={styles.noMargin}>
              {file}
            </pre>
          );
        })}
      </EventSection>
    );
  }

  if (event.sample.setup) {
    sections.push(
      <EventSection title="Setup" key={`${eventNode.id}-section-setup`}>
        <pre className={styles.code}>
          <code className="sourceCode">{event.sample.setup}</code>
        </pre>
      </EventSection>
    );
  }

  return (
    <EventPanel
      eventNodeId={eventNode.id}
      depth={eventNode.depth}
      className={className}
      title="Sample"
      icon={ApplicationIcons.sample}
      subTitle={
        event.timestamp ? formatDateTime(new Date(event.timestamp)) : undefined
      }
    >
      <div data-name="Sample" className={styles.sample}>
        <ChatView
          messages={stateObj["messages"] as ChatMessage[]}
          allowLinking={false}
        />
        <div>
          {event.sample.choices
            ? event.sample.choices.map((choice, index) => {
                return (
                  <div key={`$choice-{choice}`}>
                    {String.fromCharCode(65 + index)}) {choice}
                  </div>
                );
              })
            : ""}
          {sections.length > 0 ? (
            <div className={styles.section}>{sections}</div>
          ) : (
            ""
          )}
          {event.sample.target ? (
            <EventSection title="Target">
              {toArray(event.sample.target).map((target) => {
                return (
                  <div key={target} className={clsx("text-size-base")}>
                    {target}
                  </div>
                );
              })}
            </EventSection>
          ) : undefined}
        </div>
      </div>
      {event.sample.metadata &&
      Object.keys(event.sample.metadata).length > 0 ? (
        <MetaDataGrid
          data-name="Metadata"
          className={styles.metadata}
          entries={event.sample.metadata}
        />
      ) : (
        ""
      )}
    </EventPanel>
  );
};
