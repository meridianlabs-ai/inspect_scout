import { FC, ReactNode, useMemo } from "react";
import { useParams } from "react-router-dom";

import {
  MarkdownDivWithReferences,
  MarkdownReference,
} from "../../components/MarkdownDivWithReferences";
import {
  getRelativePathFromParams,
  parseScanResultPath,
  scanResultRoute,
} from "../../router/url";
import { ScannerCore } from "../types";
import { toMarkdownRefs } from "../utils/refs";

interface ExplanationProps {
  result?: ScannerCore;
}

export const Explanation: FC<ExplanationProps> = ({ result }): ReactNode => {
  const params = useParams<{ "*": string }>();

  // Build URL to the scan result with the appropriate query parameters
  const buildUrl = useMemo(() => {
    if (!result?.uuid) {
      return (queryParams: string) => `?${queryParams}`;
    }

    // Get the scan path from the current URL params
    const relativePath = getRelativePathFromParams(params);
    const { scanPath } = parseScanResultPath(relativePath);

    return (queryParams: string) => {
      const searchParams = new URLSearchParams(queryParams);
      return `#${scanResultRoute(scanPath, result.uuid, searchParams)}`;
    };
  }, [result?.uuid, params]);

  const refs: MarkdownReference[] = result
    ? toMarkdownRefs(result, (refId: string, type: "message" | "event") => {
        if (type === "message") {
          return buildUrl(`tab=Input&message=${encodeURIComponent(refId)}`);
        } else {
          return buildUrl(`tab=Input&event=${encodeURIComponent(refId)}`);
        }
      })
    : [];

  return (
    <MarkdownDivWithReferences
      markdown={result?.explanation || ""}
      references={refs}
    />
  );
};
