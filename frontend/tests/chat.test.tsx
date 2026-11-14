import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ChatComposer } from '../src/components/ChatComposer';
import { ChatThread, type ChatMessageItem } from '../src/components/ChatThread';
import { PlayerContext, type PlayerContextValue } from '../src/contexts/PlayerContext';

function createMockPlayerContext(overrides?: Partial<PlayerContextValue>): PlayerContextValue {
  return {
    isReady: true,
    currentTime: 10,
    duration: 3600,
    isPlaying: false,
    seekTo: vi.fn(),
    containerRef: { current: null },
    videoId: 'test1234567',
    playVideo: vi.fn(),
    pauseVideo: vi.fn(),
    ...overrides,
  };
}

describe('ChatComposer', () => {
  it('renders input, placeholder, counter and send button', () => {
    const handleSend = vi.fn();
    render(<ChatComposer onSend={handleSend} />);

    const textarea = screen.getByRole('textbox', { name: 'Ask a question' });
    expect(textarea).toBeInTheDocument();
    expect(screen.getByText('0 / 2000')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Send question' })).toBeDisabled();
  });

  it('updates text and enables send button when non-empty', () => {
    const handleSend = vi.fn();
    render(<ChatComposer onSend={handleSend} />);

    const textarea = screen.getByRole('textbox', { name: 'Ask a question' });
    fireEvent.change(textarea, { target: { value: 'What is gradient descent?' } });

    expect(screen.getByText('25 / 2000')).toBeInTheDocument();
    const sendButton = screen.getByRole('button', { name: 'Send question' });
    expect(sendButton).not.toBeDisabled();

    fireEvent.click(sendButton);
    expect(handleSend).toHaveBeenCalledTimes(1);
    expect(handleSend).toHaveBeenCalledWith('What is gradient descent?');
    // Clears value after sending
    expect(screen.getByText('0 / 2000')).toBeInTheDocument();
  });

  it('does not send on empty or whitespace-only submission', () => {
    const handleSend = vi.fn();
    render(<ChatComposer onSend={handleSend} />);

    const textarea = screen.getByRole('textbox', { name: 'Ask a question' });
    fireEvent.change(textarea, { target: { value: '   ' } });

    const sendButton = screen.getByRole('button', { name: 'Send question' });
    expect(sendButton).toBeDisabled();
    fireEvent.click(sendButton);
    expect(handleSend).not.toHaveBeenCalled();
  });

  it('submits on Enter key and allows newline on Shift+Enter', () => {
    const handleSend = vi.fn();
    render(<ChatComposer onSend={handleSend} />);

    const textarea = screen.getByRole('textbox', { name: 'Ask a question' });
    fireEvent.change(textarea, { target: { value: 'Line 1' } });

    // Shift+Enter should not submit
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: true });
    expect(handleSend).not.toHaveBeenCalled();

    // Plain Enter should submit
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false });
    expect(handleSend).toHaveBeenCalledTimes(1);
    expect(handleSend).toHaveBeenCalledWith('Line 1');
  });

  it('respects maxLength constraint', () => {
    const handleSend = vi.fn();
    render(<ChatComposer onSend={handleSend} maxLength={10} />);

    const textarea = screen.getByRole('textbox', { name: 'Ask a question' });
    fireEvent.change(textarea, { target: { value: '1234567890123' } });

    // Should not allow values exceeding maxLength
    expect(screen.getByText('0 / 10')).toBeInTheDocument();
  });

  it('disables input and button when disabled is true', () => {
    const handleSend = vi.fn();
    render(<ChatComposer onSend={handleSend} disabled={true} />);

    const textarea = screen.getByRole('textbox', { name: 'Ask a question' });
    expect(textarea).toBeDisabled();
    const sendButton = screen.getByRole('button', { name: 'Send question' });
    expect(sendButton).toBeDisabled();
  });
});

describe('ChatThread', () => {
  beforeEach(() => {
    // Mock scrollIntoView
    Element.prototype.scrollIntoView = vi.fn();
  });

  it('renders empty state when message list is empty', () => {
    render(<ChatThread messages={[]} />);
    expect(screen.getByText('NO QUESTIONS YET')).toBeInTheDocument();
    expect(screen.getByText(/Ask any question about this lecture/i)).toBeInTheDocument();
  });

  it('includes required accessibility attributes (aria-live="polite", aria-relevant="additions text")', () => {
    const { container } = render(<ChatThread messages={[]} />);
    const messageList = container.querySelector('[aria-live="polite"]');
    expect(messageList).toBeInTheDocument();
    expect(messageList).toHaveAttribute('aria-relevant', 'additions text');
  });

  it('renders user and assistant messages with YOU and TIMESLICEIQ labels and no chat bubbles', () => {
    const messages: ChatMessageItem[] = [
      {
        id: 'msg-1',
        role: 'user',
        content: 'Explain backpropagation in neural networks.',
      },
      {
        id: 'msg-2',
        role: 'assistant',
        content: 'Backpropagation computes the gradient of the loss function.',
      },
    ];

    render(<ChatThread messages={messages} />);

    expect(screen.getByText('YOU')).toBeInTheDocument();
    expect(screen.getByText('TIMESLICEIQ')).toBeInTheDocument();
    expect(screen.getByText('Explain backpropagation in neural networks.')).toBeInTheDocument();
    expect(
      screen.getByText('Backpropagation computes the gradient of the loss function.'),
    ).toBeInTheDocument();
  });

  it('renders claim blocks and citation chips using TimestampChip with click-to-seek', () => {
    const mockContext = createMockPlayerContext();
    const messages: ChatMessageItem[] = [
      {
        id: 'msg-1',
        role: 'assistant',
        blocks: [
          {
            text: 'Neural networks learn via gradient descent.',
            cites: [
              {
                chunk_id: 'c1',
                label: '01:15',
                seconds: 75,
              },
            ],
          },
          {
            text: 'Weights are adjusted backward through layers.',
            cites: [
              {
                chunk_id: 'c2',
                label: '02:40',
                seconds: 160,
              },
            ],
          },
        ],
      },
    ];

    render(
      <PlayerContext.Provider value={mockContext}>
        <ChatThread messages={messages} />
      </PlayerContext.Provider>,
    );

    expect(screen.getByText('Neural networks learn via gradient descent.')).toBeInTheDocument();
    expect(screen.getByText('Weights are adjusted backward through layers.')).toBeInTheDocument();

    const chip1 = screen.getByRole('button', { name: /Jump to 1 minute 15 seconds/i });
    expect(chip1).toBeInTheDocument();
    expect(screen.getByText('01:15')).toBeInTheDocument();

    fireEvent.click(chip1);
    expect(mockContext.seekTo).toHaveBeenCalledWith(75, true);
  });

  it('renders follow-up suggestions as ghost buttons and triggers callback on click', () => {
    const handleFollowUp = vi.fn();
    const messages: ChatMessageItem[] = [
      {
        id: 'msg-1',
        role: 'assistant',
        content: 'Transformer architectures rely on self-attention mechanisms.',
        follow_ups: [
          'How does multi-head attention work?',
          'What is the computational complexity?',
        ],
      },
    ];

    render(<ChatThread messages={messages} onSelectFollowUp={handleFollowUp} />);

    expect(screen.getByText('FOLLOW-UP SUGGESTIONS')).toBeInTheDocument();
    const followUp1 = screen.getByRole('button', { name: 'How does multi-head attention work?' });
    const followUp2 = screen.getByRole('button', { name: 'What is the computational complexity?' });

    expect(followUp1).toBeInTheDocument();
    expect(followUp2).toBeInTheDocument();

    fireEvent.click(followUp1);
    expect(handleFollowUp).toHaveBeenCalledTimes(1);
    expect(handleFollowUp).toHaveBeenCalledWith('How does multi-head attention work?');
  });

  it('renders pulsing Skeleton loading state when isLoading is true', () => {
    const { container } = render(<ChatThread messages={[]} isLoading={true} />);

    const loadingArticle = container.querySelector('[aria-busy="true"]');
    expect(loadingArticle).toBeInTheDocument();
    expect(screen.getByText('TIMESLICEIQ')).toBeInTheDocument();
    // Skeleton component renders aria-hidden="true" lines container
    const skeletonEl = loadingArticle?.querySelector('[aria-hidden="true"]');
    expect(skeletonEl).toBeInTheDocument();
  });

  it('renders inline error state with retry button', () => {
    const handleRetry = vi.fn();
    render(
      <ChatThread
        messages={[]}
        error="LLM failed to generate synthesis response."
        onRetry={handleRetry}
      />,
    );

    const alert = screen.getByRole('alert');
    expect(alert).toBeInTheDocument();
    expect(screen.getByText('LLM failed to generate synthesis response.')).toBeInTheDocument();

    const retryButton = screen.getByRole('button', { name: 'Retry' });
    expect(retryButton).toBeInTheDocument();

    fireEvent.click(retryButton);
    expect(handleRetry).toHaveBeenCalledTimes(1);
  });

  it('wires pinned ChatComposer at the bottom by default', () => {
    const handleSend = vi.fn();
    render(<ChatThread messages={[]} onSendMessage={handleSend} />);

    const textarea = screen.getByRole('textbox', { name: 'Ask a question' });
    expect(textarea).toBeInTheDocument();

    fireEvent.change(textarea, { target: { value: 'Can you summarize the introduction?' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send question' }));

    expect(handleSend).toHaveBeenCalledWith('Can you summarize the introduction?');
  });

  it('allows hiding composer via hideComposer prop', () => {
    render(<ChatThread messages={[]} onSendMessage={vi.fn()} hideComposer={true} />);
    expect(screen.queryByRole('textbox', { name: 'Ask a question' })).not.toBeInTheDocument();
  });
});
