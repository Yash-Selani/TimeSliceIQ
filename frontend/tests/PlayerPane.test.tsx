import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PlayerPane } from '../src/components/PlayerPane';
import { PlayerProvider } from '../src/contexts/PlayerContext';

describe('PlayerPane component', () => {
  it('renders the 01 · VIDEO micro-label', () => {
    render(<PlayerPane />);
    expect(screen.getByText('01 · VIDEO')).toBeInTheDocument();
  });

  it('renders a 16:9 reserved aspect-ratio player container', () => {
    const { container } = render(<PlayerPane />);
    const playerContainer = screen.getByTestId('youtube-player-container');
    expect(playerContainer).toBeInTheDocument();

    const aspectBox = container.querySelector('[class*="aspectRatioBox"]');
    expect(aspectBox).toBeInTheDocument();
  });

  it('renders video title and channel metadata below the player', () => {
    render(
      <PlayerPane
        title="MIT 6.006 Introduction to Algorithms - Lecture 1"
        channel="MIT OpenCourseWare"
      />,
    );

    const titleEl = screen.getByRole('heading', {
      name: 'MIT 6.006 Introduction to Algorithms - Lecture 1',
    });
    expect(titleEl).toBeInTheDocument();
    expect(screen.getByText('MIT OpenCourseWare')).toBeInTheDocument();
  });

  it('does not render metadata section if neither title nor channel is provided', () => {
    const { container } = render(<PlayerPane />);
    const metadata = container.querySelector('[class*="metadata"]');
    expect(metadata).toBeNull();
  });

  it('renders properly inside PlayerProvider', () => {
    render(
      <PlayerProvider videoId="dQw4w9WgXcQ">
        <PlayerPane
          title="Inside Provider Video"
          channel="Provider Channel"
        />
      </PlayerProvider>,
    );

    expect(screen.getByText('01 · VIDEO')).toBeInTheDocument();
    expect(screen.getByText('Inside Provider Video')).toBeInTheDocument();
    expect(screen.getByText('Provider Channel')).toBeInTheDocument();
  });
});
