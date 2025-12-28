import clsx from "clsx";
import { FC, Fragment, useMemo, useRef } from "react";
import { Link } from "react-router-dom";

import { basename, dirname } from "../../utils/path";
import { prettyDirUri } from "../../utils/uri";

import styles from "./Breadcrumbs.module.css";
import {
  BreadcrumbSegment,
  useBreadcrumbTruncation,
} from "./useBreadcrumbTruncation";

const kPathSeparator = "/";

interface BreadCrumbsProps {
  // The base directory path (optional, e.g., "/home/user/logs")
  // If provided, this will be displayed as the first two breadcrumb segments
  baseDir?: string;

  // The current path to build breadcrumbs from (e.g., "foo/bar/baz")
  relativePath: string;

  // Provides the route URL for a given segment path
  getRouteForSegment?: (path: string) => string | undefined;

  // Whether to disable navigation for the last segment (defaults to false)
  disableLastSegment?: boolean;

  className?: string | string[];
}

export const BreadCrumbs: FC<BreadCrumbsProps> = ({
  baseDir,
  relativePath,
  getRouteForSegment,
  disableLastSegment = false,
  className,
}) => {
  const pathContainerRef = useRef<HTMLDivElement>(null);

  const breadcrumbSegments: BreadcrumbSegment[] = useMemo(() => {
    const segments: BreadcrumbSegment[] = [];

    // Add base directory segments if provided
    if (baseDir) {
      // First segment
      const parentDir = dirname(baseDir);
      segments.push({
        text: prettyDirUri(parentDir),
        url: undefined,
      });
      // Second segment
      segments.push({
        text: basename(baseDir),
        url: getRouteForSegment ? getRouteForSegment("") : undefined,
      });
    }

    // Build segments from the current path
    const pathSegments = relativePath ? relativePath.split(kPathSeparator) : [];
    const currentSegment: string[] = [];

    for (const pathSegment of pathSegments) {
      currentSegment.push(pathSegment);
      const fullSegmentPath = currentSegment.join(kPathSeparator);
      segments.push({
        text: pathSegment,
        url: getRouteForSegment
          ? getRouteForSegment(fullSegmentPath)
          : undefined,
      });
    }

    return segments;
  }, [baseDir, relativePath, getRouteForSegment]);

  const { visibleSegments, showEllipsis } = useBreadcrumbTruncation(
    breadcrumbSegments,
    pathContainerRef
  );

  return (
    <div
      className={clsx(styles.pathContainer, className)}
      ref={pathContainerRef}
    >
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
                  isLast && disableLastSegment ? "active" : undefined
                )}
              >
                {segment.url && !(disableLastSegment && isLast) ? (
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
    </div>
  );
};
