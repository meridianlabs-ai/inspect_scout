import clsx from "clsx";
import { CSSProperties, FC, Fragment } from "react";

import { MarkdownReference } from "../MarkdownDivWithReferences";

import styles from "./MetadataGrid.module.css";
import { RenderedContent } from "./RenderedContent";

interface MetadataGridProps {
  id?: string;
  className?: string | string[];
  references?: MarkdownReference[];
  style?: CSSProperties;
  entries: Record<string, unknown>;
  options?: {
    size?: "mini" | "small";
    plain?: boolean;
    previewRefsOnHover?: boolean;
  };
}

/**
 * Renders the MetaDataView component.
 */
export const MetaDataGrid: FC<MetadataGridProps> = ({
  id,
  entries,
  className,
  references,
  style,
  options,
}) => {
  const baseId = "metadata-grid";
  const fontStyle =
    options?.size === "mini" ? "text-size-smallest" : "text-size-smaller";

  const entryEls = entryRecords(entries).map((entry, index) => {
    const id = `${baseId}-value-${index}`;
    return (
      <Fragment key={`${baseId}-record-${index}`}>
        {index !== 0 ? (
          <div
            style={{
              gridColumn: "1 / -1",
              borderBottom: `${!options?.plain ? "solid 1px var(--bs-light-border-subtle" : ""}`,
            }}
          ></div>
        ) : undefined}
        <div
          className={clsx(
            `${baseId}-key`,
            styles.cell,
            "text-style-label",
            "text-style-secondary",
            fontStyle
          )}
        >
          {entry?.name}
        </div>
        <div className={clsx(styles.value, `${baseId}-value`, fontStyle)}>
          {entry && (
            <RenderedContent
              id={id}
              entry={entry}
              references={references}
              renderOptions={{
                renderString: "markdown",
                previewRefsOnHover: options?.previewRefsOnHover,
              }}
              renderObject={(obj: any) => {
                return (
                  <MetaDataGrid
                    id={id}
                    className={clsx(styles.nested)}
                    entries={obj}
                    options={options}
                    references={references}
                  />
                );
              }}
            />
          )}
        </div>
      </Fragment>
    );
  });

  return (
    <div id={id} className={clsx(className, styles.grid)} style={style}>
      {entryEls}
    </div>
  );
};

// entries can be either a Record<string, stringable>
// or an array of record with name/value on way in
// but coerce to array of records for order
/**
 * Ensure the proper type for entries
 */
const entryRecords = (
  entries: { name: string; value: unknown }[] | Record<string, unknown>
): { name: string; value: unknown }[] => {
  if (!entries) {
    return [];
  }

  if (!Array.isArray(entries)) {
    return Object.entries(entries || {}).map(([key, value]) => {
      return { name: key, value };
    });
  } else {
    return entries;
  }
};
