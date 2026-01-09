import {
  DefaultError,
  useMutation,
  UseMutationResult,
} from "@tanstack/react-query";

import { useApi } from "../../state/store";
import { ScanJobConfig, Status } from "../../types/api-types";
import { components } from "../../types/generated";

// TODO: use actual API instead of simulatedStartJob
export const useStartScan = (): UseMutationResult<
  Status,
  DefaultError,
  ScanJobConfig
> => {
  void useApi();
  return useMutation({ mutationFn: simulatedStartJob });
};

const simulatedStartJob = (config: ScanJobConfig): Promise<Status> => {
  console.log(`XXXX starting simulated job with ${JSON.stringify(config)}`);
  return new Promise((resolve) =>
    setTimeout(
      () =>
        resolve({
          complete: false,
          errors: [],
          location: "yolocation",
          spec: {
            scan_id: "ayZ7GVrmhuuQqJ55wtBgsK",
            scan_name: "mock-scan",
            options: {},
            packages: {},
            scanners: {},
          } as components["schemas"]["ScanSpec"],
          summary: {} as components["schemas"]["Summary"],
        }),
      1000
    )
  );
};
