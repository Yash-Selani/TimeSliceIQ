import {
  useMutation,
  type UseMutationOptions,
  type UseMutationResult,
} from '@tanstack/react-query';
import {
  apiClient,
  type ApiClient,
  type ApiError,
  type IngestResponse,
} from '@/lib/api-client';

export interface UseIngestOptions
  extends Omit<UseMutationOptions<IngestResponse, ApiError, string>, 'mutationFn'> {
  client?: ApiClient;
}

export function useIngest(
  options?: UseIngestOptions,
): UseMutationResult<IngestResponse, ApiError, string> {
  const { client = apiClient, ...mutationOptions } = options ?? {};

  return useMutation<IngestResponse, ApiError, string>({
    mutationFn: (url: string) => client.ingest(url),
    ...mutationOptions,
  });
}

export default useIngest;
