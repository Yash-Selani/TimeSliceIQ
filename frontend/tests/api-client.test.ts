import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  HttpApiClient,
  ApiError,
  apiClient,
  type IngestResponse,
  type ChatRequest,
  type ChatResponse,
} from '../src/lib/api-client';

describe('HttpApiClient', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('exports singleton apiClient as an HttpApiClient instance', () => {
    expect(apiClient).toBeInstanceOf(HttpApiClient);
  });

  describe('ingest', () => {
    it('successfully posts to /api/ingest and returns parsed IngestResponse', async () => {
      const mockResponse: IngestResponse = {
        video_id: 'dQw4w9WgXcQ',
        title: 'Rick Astley - Never Gonna Give You Up',
        channel: 'Rick Astley',
        duration_s: 212,
        language: 'en',
        chunk_count: 12,
        transcript: [
          { start_s: 0, text: 'We are no strangers to love' },
        ],
      };

      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      } as Response);

      const client = new HttpApiClient();
      const result = await client.ingest('https://www.youtube.com/watch?v=dQw4w9WgXcQ');

      expect(globalThis.fetch).toHaveBeenCalledTimes(1);
      expect(globalThis.fetch).toHaveBeenCalledWith('/api/ingest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ' }),
      });
      expect(result).toEqual(mockResponse);
    });

    it('throws ApiError with code, message, and status on 400 INVALID_URL', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        json: async () => ({
          code: 'INVALID_URL',
          message: 'The URL provided is not a valid YouTube URL.',
        }),
      } as Response);

      const client = new HttpApiClient();

      await expect(client.ingest('invalid-url')).rejects.toThrow(ApiError);

      try {
        await client.ingest('invalid-url');
      } catch (err) {
        expect(err).toBeInstanceOf(ApiError);
        const apiError = err as ApiError;
        expect(apiError.code).toBe('INVALID_URL');
        expect(apiError.message).toBe('The URL provided is not a valid YouTube URL.');
        expect(apiError.status).toBe(400);
      }
    });

    it('throws ApiError on 404 NO_CAPTIONS', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: async () => ({
          code: 'NO_CAPTIONS',
          message: 'No captions or transcript found for this video.',
        }),
      } as Response);

      const client = new HttpApiClient();

      try {
        await client.ingest('https://youtube.com/watch?v=12345678901');
      } catch (err) {
        expect(err).toBeInstanceOf(ApiError);
        const apiError = err as ApiError;
        expect(apiError.code).toBe('NO_CAPTIONS');
        expect(apiError.status).toBe(404);
      }
    });

    it('falls back gracefully when response body is not valid JSON', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 502,
        statusText: 'Bad Gateway',
        json: async () => {
          throw new Error('Unexpected token');
        },
      } as unknown as Response);

      const client = new HttpApiClient();

      try {
        await client.ingest('https://youtube.com/watch?v=12345678901');
      } catch (err) {
        expect(err).toBeInstanceOf(ApiError);
        const apiError = err as ApiError;
        expect(apiError.code).toBe('LLM_FAILED');
        expect(apiError.message).toBe('Bad Gateway');
        expect(apiError.status).toBe(502);
      }
    });

    it('throws ApiError with status 0 on fetch network failure', async () => {
      globalThis.fetch = vi.fn().mockRejectedValue(new Error('Failed to fetch'));

      const client = new HttpApiClient();

      try {
        await client.ingest('https://youtube.com/watch?v=12345678901');
      } catch (err) {
        expect(err).toBeInstanceOf(ApiError);
        const apiError = err as ApiError;
        expect(apiError.code).toBe('LLM_FAILED');
        expect(apiError.message).toBe('Failed to fetch');
        expect(apiError.status).toBe(0);
      }
    });
  });

  describe('chat', () => {
    it('successfully posts to /api/chat and returns ChatResponse', async () => {
      const chatReq: ChatRequest = {
        video_id: 'dQw4w9WgXcQ',
        question: 'What is the main topic?',
      };

      const mockResponse: ChatResponse = {
        blocks: [
          {
            text: 'The video discusses never giving up.',
            cites: [{ chunk_id: 'c0', label: '00:15', seconds: 15 }],
          },
        ],
        follow_ups: ['Who is the singer?'],
      };

      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      } as Response);

      const client = new HttpApiClient();
      const result = await client.chat(chatReq);

      expect(globalThis.fetch).toHaveBeenCalledWith('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(chatReq),
      });
      expect(result).toEqual(mockResponse);
    });

    it('maps 429 RATE_LIMITED error correctly', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 429,
        statusText: 'Too Many Requests',
        json: async () => ({
          code: 'RATE_LIMITED',
          message: 'Rate limit exceeded. Please wait.',
        }),
      } as Response);

      const client = new HttpApiClient();

      try {
        await client.chat({ video_id: 'dQw4w9WgXcQ', question: 'Hello?' });
      } catch (err) {
        expect(err).toBeInstanceOf(ApiError);
        const apiError = err as ApiError;
        expect(apiError.code).toBe('RATE_LIMITED');
        expect(apiError.status).toBe(429);
      }
    });

    it('handles FastAPI 422 validation detail messages', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 422,
        statusText: 'Unprocessable Entity',
        json: async () => ({
          detail: 'Field required',
          message: 'Invalid request parameters.',
        }),
      } as Response);

      const client = new HttpApiClient();

      try {
        await client.chat({ video_id: 'bad', question: '' });
      } catch (err) {
        expect(err).toBeInstanceOf(ApiError);
        const apiError = err as ApiError;
        expect(apiError.code).toBe('INVALID_URL');
        expect(apiError.message).toBe('Invalid request parameters.');
        expect(apiError.status).toBe(422);
      }
    });
  });
});
