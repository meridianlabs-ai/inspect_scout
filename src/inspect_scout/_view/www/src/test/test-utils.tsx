import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type PropsWithChildren } from "react";

import { apiScoutServer } from "../api/api-scout-server";
import { ApiProvider } from "../state/store";

export function createTestWrapper(): React.ComponentType<PropsWithChildren> {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });

  const api = apiScoutServer();

  return function TestWrapper({ children }: PropsWithChildren) {
    return (
      <QueryClientProvider client={queryClient}>
        <ApiProvider value={api}>{children}</ApiProvider>
      </QueryClientProvider>
    );
  };
}
