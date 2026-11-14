import {
  useMutation,
  type UseMutationOptions,
  type UseMutationResult,
} from '@tanstack/react-query';
import {
  apiClient,
  type ApiClient,
  type ApiError,
  type ChatRequest,
  type ChatResponse,
} from '@/lib/api-client';

export interface UseChatOptions
  extends Omit<UseMutationOptions<ChatResponse, ApiError, ChatRequest>, 'mutationFn'> {
  client?: ApiClient;
}

export function useChat(
  options?: UseChatOptions,
): UseMutationResult<ChatResponse, ApiError, ChatRequest> {
  const { client = apiClient, ...mutationOptions } = options ?? {};

  return useMutation<ChatResponse, ApiError, ChatRequest>({
    mutationFn: (req: ChatRequest) => client.chat(req),
    ...mutationOptions,
  });
}

export default useChat;
