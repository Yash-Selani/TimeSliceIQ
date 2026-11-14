import React, { useContext, useRef } from 'react';
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
  videoId: _videoId,
  className,
}) => {
  const context = useContext(PlayerContext);
  const fallbackRef = useRef<HTMLDivElement>(null);

  // Use provider containerRef if present; otherwise fallback to local ref for isolated rendering.
  const containerRef = context ? context.containerRef : fallbackRef;

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
        />
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
