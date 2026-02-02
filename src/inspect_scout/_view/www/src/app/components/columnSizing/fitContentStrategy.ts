/**
 * Fit-content sizing strategy - measures content and sizes columns to fit.
 */

import { ColumnSizingState } from "@tanstack/react-table";

import {
  clampSize,
  DEFAULT_SIZE,
  getColumnId,
  SizingStrategy,
} from "./types";

/**
 * Measure text width using a temporary span element.
 */
function measureTextWidth(
  text: string,
  font: string,
  measureContainer: HTMLElement
): number {
  const span = document.createElement("span");
  span.style.cssText = `white-space: nowrap; font: ${font}; visibility: hidden; position: absolute;`;
  span.textContent = text;
  measureContainer.appendChild(span);
  const width = span.offsetWidth;
  measureContainer.removeChild(span);
  return width;
}

/**
 * Measure the extra width needed for header elements.
 */
function measureHeaderExtraWidth(tableElement: HTMLTableElement): number {
  const headerCell = tableElement.querySelector("th");
  if (!headerCell) return 40;

  const headerStyle = getComputedStyle(headerCell);
  const paddingLeft = parseFloat(headerStyle.paddingLeft) || 0;
  const paddingRight = parseFloat(headerStyle.paddingRight) || 0;
  const gap = parseFloat(headerStyle.gap) || 0;

  const filterButton = headerCell.querySelector("button");
  const filterButtonWidth = filterButton ? filterButton.offsetWidth : 0;

  const sortIcon = headerCell.querySelector("i");
  const sortIconWidth = sortIcon
    ? sortIcon.offsetWidth + 4
    : parseFloat(headerStyle.fontSize) || 12;

  return (
    paddingLeft + paddingRight + gap * 2 + filterButtonWidth + sortIconWidth
  );
}

/**
 * Measure the horizontal padding of table cells.
 */
function measureCellPadding(cellElement: HTMLTableCellElement | null): number {
  if (!cellElement) return 16;

  const cellStyle = getComputedStyle(cellElement);
  const paddingLeft = parseFloat(cellStyle.paddingLeft) || 0;
  const paddingRight = parseFloat(cellStyle.paddingRight) || 0;

  return paddingLeft + paddingRight;
}

export const fitContentStrategy: SizingStrategy = {
  computeSizes({
    tableElement,
    columns,
    data,
    constraints,
  }): ColumnSizingState {
    const sizing: ColumnSizingState = {};

    // Fall back to default sizes if no table element or data
    if (!tableElement || data.length === 0) {
      for (const column of columns) {
        const id = getColumnId(column);
        if (id) {
          sizing[id] = column.size ?? DEFAULT_SIZE;
        }
      }
      return sizing;
    }

    // Create a hidden container for measurement
    const measureContainer = document.createElement("div");
    measureContainer.style.cssText =
      "position: absolute; visibility: hidden; pointer-events: none; top: -9999px;";
    document.body.appendChild(measureContainer);

    try {
      const headerElement = tableElement.querySelector("th");
      const cellElement = tableElement.querySelector("td");

      const headerStyle = headerElement
        ? getComputedStyle(headerElement)
        : getComputedStyle(tableElement);
      const cellStyle = cellElement
        ? getComputedStyle(cellElement)
        : getComputedStyle(tableElement);

      const headerFont = headerStyle.font || "12px sans-serif";
      const cellFont = cellStyle.font || "12px sans-serif";

      const headerExtraWidth = measureHeaderExtraWidth(tableElement);
      const cellPadding = measureCellPadding(cellElement);

      const sampleSize = Math.min(50, data.length);

      for (const column of columns) {
        const id = getColumnId(column);
        const accessorKey = (column as { accessorKey?: string }).accessorKey;
        if (!id || !accessorKey) continue;

        const headerText = String(column.header || "");
        const headerTextWidth = measureTextWidth(
          headerText,
          headerFont,
          measureContainer
        );
        const headerWidth = headerTextWidth + headerExtraWidth;

        // Use column's textValue function if available, otherwise fall back to String()
        // If textValue returns null, skip content measurement for this column
        const getTextValue =
          column.textValue ?? ((v: unknown) => (v == null ? "-" : String(v)));

        let maxContentWidth = 0;
        let skipContentMeasurement = false;

        for (let i = 0; i < sampleSize; i++) {
          const row = data[i];
          if (!row) continue;
          const value = (row as Record<string, unknown>)[accessorKey];
          const textContent = getTextValue(value);

          // If textValue returns null, skip content measurement entirely
          if (textContent === null) {
            skipContentMeasurement = true;
            break;
          }

          const contentWidth = measureTextWidth(
            textContent,
            cellFont,
            measureContainer
          );
          maxContentWidth = Math.max(maxContentWidth, contentWidth);
        }

        // If skipping content measurement, only use header width
        if (skipContentMeasurement) {
          maxContentWidth = 0;
        }

        const contentWidthWithPadding = maxContentWidth + cellPadding;
        const idealSize = Math.max(headerWidth, contentWidthWithPadding);

        const constraint = constraints.get(id);
        if (constraint) {
          sizing[id] = clampSize(idealSize, constraint);
        } else {
          sizing[id] = idealSize;
        }
      }
    } finally {
      document.body.removeChild(measureContainer);
    }

    return sizing;
  },
};
