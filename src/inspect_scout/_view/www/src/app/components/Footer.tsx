import clsx from "clsx";
import { FC, ReactNode } from "react";

import styles from "./Footer.module.css";
import { LogPager } from "./Pager";

interface FooterProps {
  id: string;
  className?: string | string[];

  // Items
  itemCount: number;
  filteredCount?: number;

  // Progress
  progressText?: string;
  progressBar?: ReactNode;

  // Pagination
  paginated: boolean;
  pagesize?: number;
  page?: number;
  itemsPerPage?: number;

  // labels
  labels?: {
    singular: string;
    plural: string;
  };
}

export const Footer: FC<FooterProps> = ({
  id,
  className,
  itemCount,
  paginated,
  filteredCount,
  progressText,
  progressBar,
  page,
  itemsPerPage,
  labels = {
    singular: "item",
    plural: "items",
  },
}) => {
  // Get filtered count from the store
  const effectiveItemCount = filteredCount ?? itemCount;

  // Compute the start and end items
  const currentPage = page || 0;
  const pageItemCount = Math.min(
    itemsPerPage,
    effectiveItemCount - currentPage * itemsPerPage
  );
  const startItem = effectiveItemCount > 0 ? currentPage * itemsPerPage + 1 : 0;
  const endItem = startItem + pageItemCount - 1;

  return (
    <div
      id={id}
      className={clsx("text-size-smaller", styles.footer, className)}
    >
      <div className={clsx(styles.left)}>
        {progressText ? (
          <div className={clsx(styles.spinnerContainer)}>
            <div
              className={clsx("spinner-border", styles.spinner)}
              role="status"
            >
              <span className={clsx("visually-hidden")}>{progressText}...</span>
            </div>
            <div className={clsx("text-style-secondary", styles.label)}>
              {progressText}...
            </div>
          </div>
        ) : undefined}
      </div>
      <div className={clsx(styles.center)}>
        {paginated && <LogPager itemCount={effectiveItemCount} />}
      </div>
      <div className={clsx(styles.right)}>
        {progressBar ? (
          progressBar
        ) : paginated ? (
          <div>
            {effectiveItemCount === 0
              ? ""
              : filteredCount !== undefined && filteredCount !== itemCount
                ? `${startItem} - ${endItem} / ${effectiveItemCount} (${itemCount} total)`
                : `${startItem} - ${endItem} / ${effectiveItemCount}`}
          </div>
        ) : effectiveItemCount === 1 ? (
          `${effectiveItemCount} ${labels.singular}`
        ) : (
          `${effectiveItemCount} ${labels.plural}`
        )}
      </div>
    </div>
  );
};
