import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { AppShell } from '../src/components/AppShell';

describe('AppShell Component', () => {
  it('renders the header wordmark and handles logo click', () => {
    const handleLogoClick = vi.fn();
    render(<AppShell onLogoClick={handleLogoClick}><div>Content</div></AppShell>);

    const wordmark = screen.getByRole('button', { name: /timesliceiq home/i });
    expect(wordmark).toBeInTheDocument();

    fireEvent.click(wordmark);
    expect(handleLogoClick).toHaveBeenCalledTimes(1);
  });

  it('renders compact URL input for switching videos', () => {
    const handleSwitch = vi.fn();
    render(<AppShell onSwitchVideo={handleSwitch}><div>Content</div></AppShell>);

    const input = screen.getByPlaceholderText(/switch video url/i);
    expect(input).toBeInTheDocument();

    fireEvent.change(input, { target: { value: 'https://youtu.be/test12345' } });
    const switchBtn = screen.getByRole('button', { name: /switch/i });
    fireEvent.click(switchBtn);

    expect(handleSwitch).toHaveBeenCalledWith('https://youtu.be/test12345');
    expect(input).toHaveValue('');
  });

  it('renders dual-pane layout with playerPane and active tab content', () => {
    const handleTabChange = vi.fn();
    render(
      <AppShell
        playerPane={<div data-testid="player-pane">Player Mock</div>}
        chatPane={<div data-testid="chat-pane">Chat Mock</div>}
        transcriptPane={<div data-testid="transcript-pane">Transcript Mock</div>}
        activeTab="chat"
        onTabChange={handleTabChange}
      />,
    );

    expect(screen.getByTestId('player-pane')).toBeInTheDocument();
    expect(screen.getByTestId('chat-pane')).toBeInTheDocument();
    expect(screen.queryByTestId('transcript-pane')).not.toBeInTheDocument();

    // Click Transcript tab
    const transcriptTab = screen.getByRole('tab', { name: /transcript/i });
    fireEvent.click(transcriptTab);
    expect(handleTabChange).toHaveBeenCalledWith('transcript');
  });

  it('renders transcript content when activeTab is transcript', () => {
    render(
      <AppShell
        playerPane={<div data-testid="player-pane">Player Mock</div>}
        chatPane={<div data-testid="chat-pane">Chat Mock</div>}
        transcriptPane={<div data-testid="transcript-pane">Transcript Mock</div>}
        activeTab="transcript"
      />,
    );

    expect(screen.getByTestId('player-pane')).toBeInTheDocument();
    expect(screen.getByTestId('transcript-pane')).toBeInTheDocument();
    expect(screen.queryByTestId('chat-pane')).not.toBeInTheDocument();
  });
});
