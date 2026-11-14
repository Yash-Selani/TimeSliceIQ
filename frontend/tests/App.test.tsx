import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from '../src/App';
import * as apiClientModule from '../src/lib/api-client';

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe('App', () => {
  it('renders the TimeSliceIQ Landing state initially', () => {
    renderWithClient(<App />);
    expect(screen.getByRole('heading', { level: 1, name: /timesliceiq/i })).toBeInTheDocument();
    const main = screen.getByRole('main');
    expect(main).toHaveAttribute('id', 'main-content');
    expect(screen.getByLabelText(/youtube lecture url/i)).toBeInTheDocument();
  });

  it('transitions to workspace upon successful video ingest', async () => {
    const mockIngestData: apiClientModule.IngestResponse = {
      video_id: 'abc12345678',
      title: 'Neural Networks 101',
      channel: 'Deep Learning Hub',
      duration_s: 3600,
      language: 'en',
      chunk_count: 10,
      transcript: [
        { start_s: 0, text: 'Welcome to Neural Networks.' },
        { start_s: 15, text: 'Let us discuss gradient descent.' },
      ],
    };

    vi.spyOn(apiClientModule.apiClient, 'ingest').mockResolvedValueOnce(mockIngestData);

    renderWithClient(<App />);

    const input = screen.getByLabelText(/youtube lecture url/i);
    fireEvent.change(input, { target: { value: 'https://www.youtube.com/watch?v=abc12345678' } });

    const submitBtn = screen.getByRole('button', { name: /index/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText('Neural Networks 101')).toBeInTheDocument();
      expect(screen.getByText('Deep Learning Hub')).toBeInTheDocument();
    });

    // Check workspace tabs
    expect(screen.getByRole('tab', { name: /chat/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /transcript/i })).toBeInTheDocument();
  });
});
