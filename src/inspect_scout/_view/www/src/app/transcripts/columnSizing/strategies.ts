/**
 * Column sizing strategy registry.
 */

import { defaultStrategy } from "./defaultStrategy";
import { fitContentStrategy } from "./fitContentStrategy";
import { ColumnSizingStrategyKey, SizingStrategy } from "./types";

/**
 * Registry of all available sizing strategies.
 */
export const sizingStrategies: Record<ColumnSizingStrategyKey, SizingStrategy> = {
  default: defaultStrategy,
  "fit-content": fitContentStrategy,
};

/**
 * Get a sizing strategy by key.
 * Falls back to default strategy if key is not found.
 */
export function getSizingStrategy(key: ColumnSizingStrategyKey): SizingStrategy {
  return sizingStrategies[key] ?? sizingStrategies.default;
}
