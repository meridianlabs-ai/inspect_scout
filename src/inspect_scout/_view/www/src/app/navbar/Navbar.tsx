import clsx from "clsx";
import { FC, Fragment, ReactNode, useMemo, useRef } from "react";
import { Link, useParams } from "react-router-dom";

import { basename, dirname, ensureTrailingSlash } from "../../utils/path";
import { prettyDirUri } from "../../utils/uri";
import styles from "./Navbar.module.css";
import { useStore } from "../../state/store";
import { getRelativePathFromParams, scansRoute } from "../../router/url";
import { useBreadcrumbTruncation } from "./useBreadcrumbTruncation";
import { ApplicationIcons } from "../theme/icons";

interface NavbarProps {
  children?: ReactNode;
  bordered?: boolean;
}

export const Navbar: FC<NavbarProps> = ({ bordered = true, children }) => {
  const resultsDir = useStore((state) => state.resultsDir);
  const baseResultsDir = dirname(resultsDir || "");
  const baseResultsName = basename(resultsDir || "");

  const params = useParams<{ "*": string }>();
  const currentPath = getRelativePathFromParams(params);

  const pathContainerRef = useRef<HTMLDivElement>(null);
  const backUrl = scansRoute(ensureTrailingSlash(dirname(currentPath || "")));

  const segments = useMemo(() => {
    const pathSegments = currentPath ? currentPath.split("/") : [];
    const dirSegments: Array<{ text: string; url: string }> = [];
    const currentSegment = [];
    for (const pathSegment of pathSegments) {
      currentSegment.push(pathSegment);
      const segmentUrl = scansRoute(currentSegment.join("/"));
      dirSegments.push({
        text: pathSegment,
        url: segmentUrl,
      });
    }

    return [
      { text: prettyDirUri(baseResultsDir) },
      { text: baseResultsName, url: scansRoute() },
      ...dirSegments,
    ];
  }, [baseResultsDir, baseResultsName, currentPath]);

  const { visibleSegments, showEllipsis } = useBreadcrumbTruncation(
    segments,
    pathContainerRef
  );

  return (
    <nav
      className={clsx(
        "text-size-smaller",
        "header-nav",
        styles.header,
        bordered ? styles.bordered : undefined
      )}
      aria-label="breadcrumb"
      data-unsearchable={true}
    >
      <div className={clsx(styles.left)}>
        <Link to={backUrl} className={clsx(styles.toolbarButton)}>
          <i className={clsx(ApplicationIcons.navbar.back)} />
        </Link>
        <Link
          to={scansRoute()}
          className={clsx(styles.toolbarButton)}
          onClick={() => {
            //setPage(0);
          }}
        >
          <i className={clsx(ApplicationIcons.navbar.home)} />
        </Link>
        <div className={clsx(styles.pathContainer)} ref={pathContainerRef}>
          {resultsDir ? (
            <ol className={clsx("breadcrumb", styles.breadcrumbs)}>
              {visibleSegments.map((segment, index) => {
                const isLast = index === visibleSegments.length - 1;
                const shouldShowEllipsis =
                  showEllipsis && index === 1 && visibleSegments.length >= 2;

                return (
                  <Fragment key={index}>
                    {shouldShowEllipsis && (
                      <li className={clsx("breadcrumb-item", styles.ellipsis)}>
                        <span>...</span>
                      </li>
                    )}
                    <li
                      className={clsx(
                        styles.pathLink,
                        "breadcrumb-item",
                        isLast ? "active" : undefined
                      )}
                    >
                      {segment.url ? (
                        <Link to={segment.url}>{segment.text}</Link>
                      ) : (
                        <span className={clsx(styles.pathSegment)}>
                          {segment.text}
                        </span>
                      )}
                    </li>
                  </Fragment>
                );
              })}
            </ol>
          ) : (
            ""
          )}
        </div>
      </div>
      <div className={clsx(styles.right)}>{children}</div>
    </nav>
  );
};
