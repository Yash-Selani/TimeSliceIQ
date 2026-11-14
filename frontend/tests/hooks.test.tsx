import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useIngest } from '../src/hooks/useIngest';
import { useChat } from '../src/hooks/useChat';
import { ApiError, type ApiClient, type IngestResponse, type ChatResponse } from '../src/lib/api-client';

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe('useIngest hook', () => {
  it('triggers ingest on custom client and receives data', async () => {
    const mockIngestResponse: IngestResponse = {
      video_id: 'test1234567',
      title: 'Sample Video',
      channel: 'Sample Channel',
      duration_s: 120,
      language: 'en',
      chunk_count: 5,
      transcript: [{ start_s: 0, text: 'Hello world' }],
    };

    const mockClient: ApiClient = {
      ingest: vi.fn().mockResolvedValue(mockIngestResponse),
      chat: vi.fn(),
    };

    const { result } = renderHook(() => useIngest({ client: mockClient }), {
      wrapper: createWrapper(),
    });

    expect(result.current.isPending).toBe(false);

    result.current.mutate('https://youtube.com/watch?v=test1234567');

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockClient.ingest).toHaveBeenCalledWith('https://youtube.com/watch?v=test1234567');
    expect(result.current.data).toEqual(mockIngestResponse);
  });

  it('handles error state when ingest rejects with ApiError', async () => {
    const error = new ApiError('NO_CAPTIONS', 'Captions missing', 404);
    const mockClient: ApiClient = {
      ingest: vi.fn().mockRejectedValue(error),
      chat: vi.fn(),
    };

    const { result } = renderHook(() => useIngest({ client: mockClient }), {
      wrapper: createWrapper(),
    });

    result.current.mutate('https://youtube.com/watch?v=nocaptions');

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBe(error);
    expect(result.current.error?.code).toBe('NO_CAPTIONS');
    expect(result.current.error?.status).toBe(404);
  });
});

describe('useChat hook', () => {
  it('triggers chat on custom client and receives response', async () => {
    const mockChatResponse: ChatResponse = {
      blocks: [
        {
          text: 'This is the answer.',
          cites: [{ chunk_id: 'c1', label: '01:00', seconds: 60 }],
        },
      ],
      follow_ups: ['Can you elaborate?'],
    };

    const mockClient: ApiClient = {
      ingest: vi.fn(),
      chat: vi.fn().mockResolvedValue(mockChatResponse),
    };

    const { result } = renderHook(() => useChat({ client: mockClient }), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      video_id: 'test1234567',
      question: 'What is this?',
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockClient.chat).toHaveBeenCalledWith({
      video_id: 'test1234567',
      question: 'What is this?',
    });
    expect(result.current.data).toEqual(mockChatResponse);
  });

  it('handles error state when chat rejects with ApiError', async () => {
    const error = new ApiError('RATE_LIMITED', 'Rate limited', 429);
    const mockClient: ApiClient = {
      ingest: vi.fn(),
      chat: vi.fn().mockRejectedValue(error),
    };

    const { result } = renderHook(() => useChat({ client: mockClient }), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      video_id: 'test1234567',
      question: 'What is this?',
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBe(error);
    expect(result.current.error?.code).toBe('RATE_LIMITED');
    expect(result.current.error?.status).toBe(429);
  });
});
