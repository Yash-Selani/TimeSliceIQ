import type { components } from '@/types/api';

export type IngestRequest = components['schemas']['IngestRequest'];
export type IngestResponse = components['schemas']['IngestResponse'];
export type ChatRequest = components['schemas']['ChatRequest'];
export type ChatResponse = components['schemas']['ChatResponse'];
export type ErrorResponse = components['schemas']['ErrorResponse'];
export type ErrorCode = components['schemas']['ErrorCode'];
export type TranscriptLine = components['schemas']['TranscriptLine'];
export type Citation = components['schemas']['Citation'];
export type AnswerBlock = components['schemas']['AnswerBlock'];
export type ChatMessage = components['schemas']['ChatMessage'];

const KNOWN_ERROR_CODES: ReadonlySet<ErrorCode> = new Set<ErrorCode>([
  'INVALID_URL',
  'NO_CAPTIONS',
  'VIDEO_UNAVAILABLE',
  'TRANSCRIPT_BLOCKED',
  'RATE_LIMITED',
  'LLM_FAILED',
]);

function resolveErrorCode(code: unknown, status: number): ErrorCode {
  if (typeof code === 'string' && KNOWN_ERROR_CODES.has(code as ErrorCode)) {
    return code as ErrorCode;
  }
  if (status === 429) return 'RATE_LIMITED';
  if (status === 400 || status === 422) return 'INVALID_URL';
  if (status === 404) return 'VIDEO_UNAVAILABLE';
  return 'LLM_FAILED';
}

export class ApiError extends Error {
  code: ErrorCode;
  override message: string;
  status: number;

  constructor(code: ErrorCode, message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.message = message;
    this.status = status;
    Object.setPrototypeOf(this, ApiError.prototype);
  }
}

export interface ApiClient {
  ingest(url: string): Promise<IngestResponse>;
  chat(req: ChatRequest): Promise<ChatResponse>;
}

export class HttpApiClient implements ApiClient {
  private readonly baseUrl: string;

  constructor(baseUrl: string = '') {
    this.baseUrl = baseUrl;
  }

  private async request<T>(endpoint: string, options: RequestInit): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    let response: Response;

    try {
      response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      });
    } catch (networkError) {
      const msg = networkError instanceof Error ? networkError.message : 'Network request failed';
      throw new ApiError('LLM_FAILED', msg, 0);
    }

    if (!response.ok) {
      let code: ErrorCode = resolveErrorCode(undefined, response.status);
      let message = response.statusText || `Request failed with status ${response.status}`;

      try {
        const errorData = await response.json();
        if (errorData && typeof errorData === 'object') {
          if (typeof errorData.code === 'string') {
            code = resolveErrorCode(errorData.code, response.status);
          }
          if (typeof errorData.message === 'string') {
            message = errorData.message;
          } else if (typeof errorData.detail === 'string') {
            message = errorData.detail;
          }
        }
      } catch {
        // Response body wasn't JSON or could not be parsed; keep default statusText/message
      }

      throw new ApiError(code, message, response.status);
    }

    return (await response.json()) as T;
  }

  async ingest(url: string): Promise<IngestResponse> {
    return this.request<IngestResponse>('/api/ingest', {
      method: 'POST',
      body: JSON.stringify({ url }),
    });
  }

  async chat(req: ChatRequest): Promise<ChatResponse> {
    return this.request<ChatResponse>('/api/chat', {
      method: 'POST',
      body: JSON.stringify(req),
    });
  }
}

export const apiClient: ApiClient = new HttpApiClient();
export default apiClient;
