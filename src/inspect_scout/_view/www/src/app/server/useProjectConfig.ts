import {
  DefaultError,
  useMutation,
  UseMutationResult,
  useQueryClient,
} from "@tanstack/react-query";

import { useApi } from "../../state/store";
import { ProjectConfig, ProjectConfigInput } from "../../types/api-types";
import { AsyncData } from "../../utils/asyncData";
import { useAsyncDataFromQuery } from "../../utils/asyncDataFromQuery";

export type ProjectConfigWithEtag = {
  config: ProjectConfig;
  etag: string;
};

/**
 * Loads project configuration from scout.yaml.
 *
 * Returns both the config and an etag for optimistic concurrency control.
 *
 * Automatic refetching is disabled to support optimistic locking:
 * - External changes are detected via etag mismatch on save (412 error)
 * - User explicitly chooses to reload or force save on conflict
 */
export const useProjectConfig = (): AsyncData<ProjectConfigWithEtag> => {
  const api = useApi();

  return useAsyncDataFromQuery({
    queryKey: ["project-config"],
    queryFn: () => api.getProjectConfig(),
    staleTime: Infinity,
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    refetchOnReconnect: false,
  });
};

/**
 * Mutation hook for updating project configuration.
 *
 * Updates scout.yaml while preserving comments and formatting.
 * Requires the current etag for optimistic concurrency control.
 *
 * On success, updates the query cache with the new config and etag.
 * On 412 Precondition Failed, the config was modified externally.
 */
export const useUpdateProjectConfig = (): UseMutationResult<
  ProjectConfigWithEtag,
  DefaultError,
  { config: ProjectConfigInput; etag: string | null }
> => {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ config, etag }) => api.updateProjectConfig(config, etag),
    onSuccess: (data) => {
      // Update cache with new config and etag
      queryClient.setQueryData(["project-config"], data);
      queryClient
        .invalidateQueries({ queryKey: ["config"] })
        .catch(console.log);
    },
  });
};

/*
import { useProjectConfig, useUpdateProjectConfig } from "./server/useProjectConfig";                                
                                                                                                                      
function ConfigEditor() {                                                                                            
  const configData = useProjectConfig();                                                                             
  const mutation = useUpdateProjectConfig();                                                                         
                                                                                                                      
  if (configData.loading) return <Loading />;                                                                        
  if (configData.error) return <Error error={configData.error} />;                                                   
                                                                                                                      
  const { config, etag } = configData.data;                                                                          
                                                                                                                      
  const handleSave = async (newConfig: ProjectConfigInput) => {                                                      
    try {                                                                                                            
      await mutation.mutateAsync({ config: newConfig, etag });                                                       
    } catch (error) {                                                                                                
      if (error instanceof ApiError && error.status === 412) {                                                       
        // Config was modified externally - prompt user to refresh                                                   
      }                                                                                                              
    }                                                                                                                
  };                                                                                                                 
  return <Form config={config} onSave={handleSave} />;                                                               
}                             

*/
