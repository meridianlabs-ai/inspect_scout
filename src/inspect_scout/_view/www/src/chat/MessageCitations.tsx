import clsx from "clsx";
import { FC, Fragment, PropsWithChildren, ReactElement } from "react";

import { UrlCitation as UrlCitationType } from "../types/api-types";
import { decodeHtmlEntities } from "../utils/html";

import styles from "./MessageCitations.module.css";
import { Citation } from "./types";

export interface MessageCitationsProps {
  citations: Citation[];
}

export const MessageCitations: FC<MessageCitationsProps> = ({ citations }) => {
  if (citations.length === 0) {
    return undefined;
  }

  return (
    <div className={clsx(styles.citations, "text-size-smallest")}>
      {citations.map((citation, index) => (
        <Fragment key={index}>
          <span>{index + 1}</span>
          <MessageCitation citation={citation} />
        </Fragment>
      ))}
    </div>
  );
};

interface MessageCitationProps {
  citation: Citation;
}

const MessageCitation: FC<MessageCitationProps> = ({ citation }) => {
  const innards = decodeHtmlEntities(
    citation.title ??
      (typeof citation.cited_text === "string"
        ? citation.cited_text
        : citation.type === "url"
          ? citation.url
          : "")
  );
  return citation.type === "url" ? (
    <UrlCitation citation={citation}>{innards}</UrlCitation>
  ) : (
    <OtherCitation>{innards}</OtherCitation>
  );
};

const UrlCitation: FC<PropsWithChildren<{ citation: UrlCitationType }>> = ({
  children,
  citation,
}): ReactElement => (
  <a
    href={citation.url}
    target="_blank"
    rel="noopener noreferrer"
    className={clsx(styles.citationLink)}
    title={
      citation.cited_text && typeof citation.cited_text === "string"
        ? `${citation.cited_text}\n${citation.url}`
        : citation.url
    }
  >
    {children}
  </a>
);

const OtherCitation: FC<PropsWithChildren> = ({ children }): ReactElement => (
  <>{children}</>
);
