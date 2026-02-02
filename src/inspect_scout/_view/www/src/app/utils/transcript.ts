import { Transcript } from "../../types/api-types";

interface TaskNameParts {
  taskSet?: string | null;
  taskId?: string | number | null;
  taskRepeat?: number | null;
}

/**
 * Formats task name parts into a display string.
 *
 * Produces a string like "taskSet/taskId (taskRepeat)" with optional parts:
 * - If only taskSet: "taskSet"
 * - If only taskId: "taskId"
 * - If both: "taskSet/taskId"
 * - With repeat: "taskSet/taskId (1)"
 *
 * @param parts - Object containing taskSet, taskId, and taskRepeat
 * @returns Formatted task name string, or undefined if no parts are available
 */
export function formatTaskName(parts: TaskNameParts): string | undefined {
  const { taskSet, taskId, taskRepeat } = parts;

  if (!taskSet && !taskId && taskRepeat === undefined) {
    return undefined;
  }

  const nameParts: string[] = [];

  if (taskSet) {
    nameParts.push(taskSet);
  }

  if (taskId !== undefined && taskId !== null) {
    if (nameParts.length > 0) {
      nameParts.push("/");
    }
    nameParts.push(String(taskId));
  }

  if (taskRepeat !== undefined && taskRepeat !== null) {
    nameParts.push(` (${taskRepeat})`);
  }

  return nameParts.length > 0 ? nameParts.join("") : undefined;
}

/**
 * Gets the display name for a transcript.
 *
 * Uses taskSet/taskId/taskRepeat when available, falls back to task_id.
 *
 * @param transcript - The transcript object, or undefined if loading
 * @returns The transcript display name, or undefined if transcript is undefined
 */
export function getTranscriptDisplayName(
  transcript: Transcript | undefined
): string | undefined {
  if (!transcript) return undefined;

  // Try to build a meaningful name from task parts
  const formattedName = formatTaskName({
    taskSet: transcript.task_set,
    taskId: transcript.task_id,
    taskRepeat: transcript.task_repeat,
  });

  // Fall back to task_id if no formatted name available
  return formattedName ?? transcript.task_id ?? undefined;
}
