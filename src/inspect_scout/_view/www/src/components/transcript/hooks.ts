import { useMemo } from "react";

import { useStore } from "../../state/store";

export const useCollapseTranscriptEvent = (
  scope: string,
  id: string
): [boolean, (collapsed: boolean) => void] => {
  const collapsed = useStore((state) => state.transcriptCollapsedEvents);
  const collapseEvent = useStore((state) => state.setTranscriptCollapsedEvent);

  return useMemo(() => {
    const isCollapsed = collapsed !== null && collapsed[scope]?.[id] === true;
    const set = (value: boolean) => {
      collapseEvent(scope, id, value);
    };
    return [isCollapsed, set];
  }, [collapsed, collapseEvent, id]);
};
