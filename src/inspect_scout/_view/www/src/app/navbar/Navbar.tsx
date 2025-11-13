import clsx from "clsx";
import { FC, Fragment, ReactNode, useMemo, useRef } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import {
  getRelativePathFromParams,
  isValidScanPath,
  parseScanResultPath,
  scanRoute,
  scansRoute,
} from "../../router/url";
import { useStore } from "../../state/store";
import { basename, dirname } from "../../utils/path";
import { prettyDirUri } from "../../utils/uri";
import { ApplicationIcons } from "../appearance/icons";

import styles from "./Navbar.module.css";
import { useBreadcrumbTruncation } from "./useBreadcrumbTruncation";

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
  const singleFileMode = useStore((state) => state.singleFileMode);
  const [searchParams] = useSearchParams();

  const pathContainerRef = useRef<HTMLDivElement>(null);

  // Check if we're on a scan result page and calculate the appropriate back URL
  const { scanPath, scanResultUuid } = parseScanResultPath(currentPath);
  const backUrl = scanResultUuid
    ? scanRoute(scanPath, searchParams)
    : !singleFileMode
      ? scansRoute(dirname(currentPath || ""))
      : undefined;

  const segments = useMemo(() => {
    const pathSegments = currentPath ? currentPath.split("/") : [];
    const dirSegments: Array<{ text: string; url: string }> = [];
    const currentSegment = [];
    for (const pathSegment of pathSegments) {
      currentSegment.push(pathSegment);
      const fullSegmentPath = currentSegment.join("/");
      // Check if this segment path contains a valid scan_id pattern
      // If so, use scanRoute instead of scansRoute
      const segmentUrl = isValidScanPath(fullSegmentPath)
        ? scanRoute(fullSegmentPath, searchParams)
        : scansRoute(fullSegmentPath);
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
  }, [baseResultsDir, baseResultsName, currentPath, searchParams]);

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
        {backUrl && (
          <Link to={backUrl} className={clsx(styles.toolbarButton)}>
            <i className={clsx(ApplicationIcons.navbar.back)} />
          </Link>
        )}
        {!singleFileMode && (
          <Link
            to={scansRoute()}
            className={clsx(styles.toolbarButton)}
            onClick={() => {
              //setPage(0);
            }}
          >
            <i className={clsx(ApplicationIcons.navbar.home)} />
          </Link>
        )}
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
                        isLast && !singleFileMode ? "active" : undefined
                      )}
                    >
                      {segment.url && !singleFileMode && !isLast ? (
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
      <div
        className={clsx(
          styles.right,
          children ? styles.hasChildren : undefined
        )}
      >
        {children}
      </div>
    </nav>
  );
};
