import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { Landing } from '../src/components/Landing';

describe('Landing Component', () => {
  it('renders oversized headline and subhead', () => {
    render(<Landing onSubmit={vi.fn()} />);

    expect(screen.getByRole('heading', { level: 1, name: /timesliceiq/i })).toBeInTheDocument();
    expect(
      screen.getByText(/paste a lecture url to ask questions with millisecond-exact citations/i),
    ).toBeInTheDocument();
  });

  it('renders a prominent URL input and submits when filled', () => {
    const handleSubmit = vi.fn();
    render(<Landing onSubmit={handleSubmit} />);

    const input = screen.getByLabelText(/youtube lecture url/i);
    expect(input).toBeInTheDocument();

    fireEvent.change(input, { target: { value: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ' } });
    const submitBtn = screen.getByRole('button', { name: /index/i });
    fireEvent.click(submitBtn);

    expect(handleSubmit).toHaveBeenCalledWith('https://www.youtube.com/watch?v=dQw4w9WgXcQ');
  });

  it('shows validation error when submitting whitespace or empty URL', () => {
    const handleSubmit = vi.fn();
    render(<Landing onSubmit={handleSubmit} />);

    const form = screen.getByRole('button', { name: /index/i }).closest('form');
    if (form) {
      fireEvent.submit(form);
    }

    expect(handleSubmit).not.toHaveBeenCalled();
    expect(screen.getByRole('alert')).toHaveTextContent(/please enter a youtube video url/i);
  });

  it('disables input and button during isLoading', () => {
    render(<Landing onSubmit={vi.fn()} isLoading={true} />);

    const input = screen.getByLabelText(/youtube lecture url/i);
    const submitBtn = screen.getByRole('button', { name: /indexing/i });

    expect(input).toBeDisabled();
    expect(submitBtn).toBeDisabled();
  });

  it('displays external error when provided', () => {
    render(<Landing onSubmit={vi.fn()} error="Video unavailable" />);

    const alert = screen.getByRole('alert');
    expect(alert).toHaveTextContent('Video unavailable');
  });
});
