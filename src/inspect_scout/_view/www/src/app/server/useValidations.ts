import { skipToken, useMutation, useQueryClient } from "@tanstack/react-query";

import { useApi } from "../../state/store";
import {
  CreateValidationSetRequest,
  ValidationCase,
  ValidationCaseRequest,
} from "../../types/api-types";
import { AsyncData } from "../../utils/asyncData";
import { useAsyncDataFromQuery } from "../../utils/asyncDataFromQuery";

/**
 * Query key factory for validation-related queries.
 * Centralizes key definitions to ensure consistency between queries and invalidations.
 */
export const validationQueryKeys = {
  sets: () => ["validationSets"] as const,
  cases: (uri: string | typeof skipToken) => ["validationCases", uri] as const,
  case: (params: { url: string; caseId: string } | typeof skipToken) =>
    ["validationCase", params] as const,
};

/**
 * Hook to fetch all validation set URIs in the project.
 */
export const useValidationSets = (): AsyncData<string[]> => {
  const api = useApi();
  return useAsyncDataFromQuery({
    queryKey: validationQueryKeys.sets(),
    queryFn: () => api.getValidationSets(),
    staleTime: 60 * 1000,
  });
};

/**
 * Hook to fetch validation cases for a specific validation set.
 */
export const useValidationCases = (
  uri: string | typeof skipToken
): AsyncData<ValidationCase[]> => {
  const api = useApi();
  return useAsyncDataFromQuery({
    queryKey: validationQueryKeys.cases(uri),
    queryFn: uri === skipToken ? skipToken : () => api.getValidationCases(uri),
    staleTime: 60 * 1000,
    enabled: uri !== skipToken,
  });
};

/**
 * Hook to fetch a single validation case by URI and case ID.
 */
export const useValidationCase = (
  params: { url: string; caseId: string } | typeof skipToken
): AsyncData<ValidationCase> => {
  const api = useApi();

  return useAsyncDataFromQuery({
    queryKey: validationQueryKeys.case(params),
    queryFn:
      params === skipToken
        ? skipToken
        : () => api.getValidationCase(params.url, params.caseId),
    staleTime: 60 * 1000,
  });
};

/**
 * Hook to create a new validation set.
 */
export const useCreateValidationSet = () => {
  const queryClient = useQueryClient();
  const api = useApi();
  return useMutation<string, Error, CreateValidationSetRequest>({
    mutationFn: (request) => api.createValidationSet(request),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: validationQueryKeys.sets(),
      });
    },
  });
};

/**
 * Hook to update a validation case (upsert).
 */
export const useUpdateValidationCase = (uri: string) => {
  const queryClient = useQueryClient();
  const api = useApi();
  return useMutation<
    ValidationCase,
    Error,
    { caseId: string; data: ValidationCaseRequest }
  >({
    mutationFn: ({ caseId, data }) =>
      api.upsertValidationCase(uri, caseId, data),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({
        queryKey: validationQueryKeys.cases(uri),
      });
      void queryClient.invalidateQueries({
        queryKey: validationQueryKeys.case({
          url: uri,
          caseId: variables.caseId,
        }),
      });
    },
  });
};

/**
 * Hook to delete a single validation case.
 */
export const useDeleteValidationCase = (uri: string) => {
  const queryClient = useQueryClient();
  const api = useApi();
  return useMutation<boolean, Error, string>({
    mutationFn: (caseId) => api.deleteValidationCase(uri, caseId),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: validationQueryKeys.cases(uri),
      });
    },
  });
};

/**
 * Hook to delete multiple validation cases (bulk delete).
 * Uses Promise.allSettled to handle partial failures gracefully.
 */
export const useBulkDeleteValidationCases = (uri: string) => {
  const queryClient = useQueryClient();
  const api = useApi();
  return useMutation<{ succeeded: number; failed: number }, Error, string[]>({
    mutationFn: async (caseIds) => {
      const results = await Promise.allSettled(
        caseIds.map((id) => api.deleteValidationCase(uri, id))
      );

      const succeeded = results.filter((r) => r.status === "fulfilled").length;
      const failed = results.filter((r) => r.status === "rejected").length;

      // Always invalidate cache if at least one succeeded
      if (succeeded > 0) {
        void queryClient.invalidateQueries({
          queryKey: validationQueryKeys.cases(uri),
        });
      }

      // Throw if all failed
      if (failed === results.length) {
        const errors = results
          .filter((r): r is PromiseRejectedResult => r.status === "rejected")
          .map((r) => r.reason);
        throw new Error(`All deletions failed: ${errors.join(", ")}`);
      }

      return { succeeded, failed };
    },
  });
};

/**
 * Hook to delete an entire validation set.
 */
export const useDeleteValidationSet = () => {
  const queryClient = useQueryClient();
  const api = useApi();
  return useMutation<boolean, Error, string>({
    mutationFn: (uri) => api.deleteValidationSet(uri),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: validationQueryKeys.sets(),
      });
    },
  });
};

/**
 * Hook to rename a validation set.
 */
export const useRenameValidationSet = () => {
  const queryClient = useQueryClient();
  const api = useApi();
  return useMutation<string, Error, { uri: string; newName: string }>({
    mutationFn: ({ uri, newName }) => api.renameValidationSet(uri, newName),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: validationQueryKeys.sets(),
      });
    },
  });
};
