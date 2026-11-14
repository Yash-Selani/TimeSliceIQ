import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { TimestampChip } from '../src/components/TimestampChip';
import { PlayerContext, type PlayerContextValue } from '../src/contexts/PlayerContext';

function createMockPlayerContext(overrides?: Partial<PlayerContextValue>): PlayerContextValue {
  return {
    isReady: true,
    currentTime: 0,
    duration: 3600,
    isPlaying: false,
    seekTo: vi.fn(),
    containerRef: { current: null },
    videoId: 'abc12345',
    playVideo: vi.fn(),
    pauseVideo: vi.fn(),
    player: null,
    ...overrides,
  };
}

function renderWithPlayer(
  ui: React.ReactElement,
  mockContext: PlayerContextValue = createMockPlayerContext(),
) {
  return render(
    <PlayerContext.Provider value={mockContext}>
      {ui}
    </PlayerContext.Provider>,
  );
}

describe('TimestampChip', () => {
  it('renders tabular formatted timestamp from seconds (< 1 hr)', () => {
    renderWithPlayer(<TimestampChip seconds={75} />);
    const button = screen.getByRole('button', { name: 'Jump to 1 minute 15 seconds' });
    expect(button).toBeInTheDocument();
    expect(button).toHaveTextContent('01:15');
    expect(button).toHaveAttribute('data-seconds', '75');
  });

  it('renders tabular formatted timestamp from seconds (>= 1 hr)', () => {
    renderWithPlayer(<TimestampChip seconds={3665} />);
    const button = screen.getByRole('button', { name: 'Jump to 1 hour 1 minute 5 seconds' });
    expect(button).toBeInTheDocument();
    expect(button).toHaveTextContent('01:01:05');
  });

  it('allows custom label and ariaLabel overrides', () => {
    renderWithPlayer(
      <TimestampChip
        seconds={120}
        label="Intro section"
        ariaLabel="Jump to intro section at 2 minutes"
      />,
    );
    const button = screen.getByRole('button', {
      name: 'Jump to intro section at 2 minutes',
    });
    expect(button).toHaveTextContent('Intro section');
  });

  it('reflects active state via aria-pressed and active class', () => {
    renderWithPlayer(<TimestampChip seconds={60} active />);
    const button = screen.getByRole('button', { name: 'Jump to 1 minute' });
    expect(button).toHaveAttribute('aria-pressed', 'true');
  });

  it('calls player.seekTo and dispatches timesliceiq:seek event on click', () => {
    const mockContext = createMockPlayerContext();
    const handleSeekEvent = vi.fn();
    window.addEventListener('timesliceiq:seek', handleSeekEvent);

    renderWithPlayer(<TimestampChip seconds={765} />, mockContext);

    const button = screen.getByRole('button', { name: 'Jump to 12 minutes 45 seconds' });
    fireEvent.click(button);

    // Verified seekTo call
    expect(mockContext.seekTo).toHaveBeenCalledTimes(1);
    expect(mockContext.seekTo).toHaveBeenCalledWith(765, true);

    // Verified custom DOM event
    expect(handleSeekEvent).toHaveBeenCalledTimes(1);
    const event = handleSeekEvent.mock.calls[0][0] as CustomEvent<{ seconds: number }>;
    expect(event.detail).toEqual({ seconds: 765 });

    window.removeEventListener('timesliceiq:seek', handleSeekEvent);
  });

  it('throws informative error when rendered outside PlayerProvider', () => {
    // Suppress console.error in vitest for intentional throw test
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => render(<TimestampChip seconds={90} />)).toThrow(
      'usePlayerContext must be used within a <PlayerProvider>',
    );
    consoleSpy.mockRestore();
  });

  it('calls optional onClick prop', () => {
    const handleClick = vi.fn();
    renderWithPlayer(<TimestampChip seconds={30} onClick={handleClick} />);
    fireEvent.click(screen.getByRole('button', { name: 'Jump to 30 seconds' }));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });
});
