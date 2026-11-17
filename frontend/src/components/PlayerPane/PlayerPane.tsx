import React, { useContext, useRef, useEffect, useState } from 'react';
import { PlayerContext } from '../../contexts/PlayerContext';
import styles from './PlayerPane.module.css';

export interface PlayerPaneProps {
  title?: string;
  channel?: string;
  videoId?: string;
  className?: string;
}

export const PlayerPane: React.FC<PlayerPaneProps> = ({
  title,
  channel,
  videoId,
  className,
}) => {
  const context = useContext(PlayerContext);
  const fallbackRef = useRef<HTMLDivElement>(null);

  // Use provider containerRef if present; otherwise fallback to local ref for isolated rendering.
  const containerRef = context ? context.containerRef : fallbackRef;
  const activeVideoId = videoId || context?.videoId;
  const [directEmbed, setDirectEmbed] = useState(false);

  useEffect(() => {
    // If after 1.2s no iframe exists in container, fall back to direct iframe embed
    const timer = setTimeout(() => {
      if (containerRef.current && !containerRef.current.querySelector('iframe') && activeVideoId) {
        setDirectEmbed(true);
      }
    }, 1200);

    return () => clearTimeout(timer);
  }, [containerRef, activeVideoId]);

  return (
    <section
      className={className ? `${styles.playerPane} ${className}` : styles.playerPane}
      aria-label="Video Player"
    >
      <header className={styles.header}>
        <span className={styles.microLabel}>01 · VIDEO</span>
      </header>

      <div className={styles.aspectRatioBox}>
        <div
          ref={containerRef}
          className={styles.playerContainer}
          data-testid="youtube-player-container"
        >
          {directEmbed && activeVideoId && (
            <iframe
              src={`https://www.youtube-nocookie.com/embed/${activeVideoId}?enablejsapi=1&origin=${encodeURIComponent(typeof window !== 'undefined' ? window.location.origin : '')}`}
              title={title || 'YouTube Video Player'}
              width="100%"
              height="100%"
              style={{ border: 0, width: '100%', height: '100%' }}
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
              allowFullScreen
            />
          )}
        </div>
      </div>

      {(title || channel) && (
        <footer className={styles.metadata}>
          {title && <h2 className={styles.title}>{title}</h2>}
          {channel && <p className={styles.channel}>{channel}</p>}
        </footer>
      )}
    </section>
  );
};

export default PlayerPane;
