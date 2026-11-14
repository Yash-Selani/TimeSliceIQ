import React from 'react';
import styles from './ErrorState.module.css';
import type { EmptyStateProps } from './types';

export const EmptyState: React.FC<EmptyStateProps> = ({
  headline = 'NO VIDEO LOADED',
  body = 'Paste a YouTube URL in the header to index the lecture and begin questioning.',
  statusLabel = 'STANDBY // 00',
  hint = 'PASTE YOUTUBE URL IN HEADER INPUT',
  action,
  className = '',
  style,
}) => {
  const containerClassName = `${styles.emptyContainer} ${className}`.trim();

  return (
    <section
      role="status"
      aria-label="No video loaded"
      className={containerClassName}
      style={style}
      data-testid="empty-state"
    >
      <div className={styles.emptyMeta}>
        <span>STATUS: {statusLabel}</span>
      </div>

      <h2 className={styles.emptyTitle}>{headline}</h2>

      <hr className={styles.divider} />

      <p className={styles.emptyDescription}>{body}</p>

      {hint && (
        <div className={styles.hintLine} aria-hidden="true">
          <span>INPUT:</span>
          <span className={styles.hintKey}>{hint}</span>
        </div>
      )}

      {action && <div className={styles.emptyActionSlot}>{action}</div>}
    </section>
  );
};

export default EmptyState;
