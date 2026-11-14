import React from 'react';
import styles from './ErrorState.module.css';
import type { LoadingStageIdentifier, LoadingStateProps } from './types';

const DEFAULT_STAGES = [
  '1. Fetching captions...',
  '2. Indexing concepts...',
  '3. Ready',
];

const resolveStageIndex = (stage: LoadingStageIdentifier): number => {
  if (typeof stage === 'number') {
    return Math.max(1, Math.min(3, stage));
  }
  switch (stage) {
    case 'captions':
      return 1;
    case 'indexing':
      return 2;
    case 'ready':
      return 3;
    default:
      return 1;
  }
};

export const LoadingState: React.FC<LoadingStateProps> = ({
  stage = 1,
  stages = DEFAULT_STAGES,
  title = 'PIPELINE PROCESSING',
  statusMessage,
  showSkeleton = true,
  className = '',
  style,
}) => {
  const currentStageIndex = resolveStageIndex(stage);
  const totalStages = stages.length;
  const progressPercentage = Math.round((currentStageIndex / totalStages) * 100);

  const containerClassName = `${styles.loadingContainer} ${className}`.trim();

  return (
    <div
      role="status"
      aria-live="polite"
      aria-label={`${title} - Stage ${currentStageIndex} of ${totalStages}`}
      className={containerClassName}
      style={style}
      data-testid="loading-state"
      data-stage={currentStageIndex}
    >
      <div className={styles.loadingHeader}>
        <span className={styles.loadingMeta}>{title}</span>
        <span className={styles.loadingStageCounter}>
          STAGE {String(currentStageIndex).padStart(2, '0')} / {String(totalStages).padStart(2, '0')}
        </span>
      </div>

      {/* Hairline Progress Bar */}
      <div
        className={styles.progressTrack}
        role="progressbar"
        aria-valuenow={progressPercentage}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className={styles.progressBar}
          style={{ width: `${progressPercentage}%` }}
        />
      </div>

      {/* Staged Steps */}
      <div className={styles.stageList}>
        {stages.map((stageText, idx) => {
          const stepNumber = idx + 1;
          const isActive = stepNumber === currentStageIndex;
          const isCompleted = stepNumber < currentStageIndex;
          const isUpcoming = stepNumber > currentStageIndex;

          let itemClass = styles.stageItem;
          let statusClass = styles.stageStatus;
          let statusText = '[QUEUED]';

          if (isActive) {
            itemClass += ` ${styles.stageItemActive}`;
            statusClass += ` ${styles.stageStatusActive}`;
            statusText = stepNumber === totalStages ? '[COMPLETE]' : '[ACTIVE]';
          } else if (isCompleted) {
            itemClass += ` ${styles.stageItemCompleted}`;
            statusClass += ` ${styles.stageStatusCompleted}`;
            statusText = '[DONE]';
          } else if (isUpcoming) {
            itemClass += ` ${styles.stageItemUpcoming}`;
            statusClass += ` ${styles.stageStatusUpcoming}`;
            statusText = '[QUEUED]';
          }

          return (
            <div key={stageText} className={itemClass}>
              <span className={styles.stageText}>
                {stageText}
              </span>
              <span className={statusClass} aria-hidden="true">
                {statusText}
              </span>
            </div>
          );
        })}
      </div>

      {statusMessage && (
        <p className={styles.errorDescription}>{statusMessage}</p>
      )}

      {/* Minimalist Hairline Wireframe Skeleton */}
      {showSkeleton && (
        <div className={styles.skeletonGroup} aria-hidden="true">
          <div className={styles.skeletonMeta}>TRANSCRIPT BUFFER</div>
          <div className={styles.skeletonBlock} />
          <div className={`${styles.skeletonBlock} ${styles.skeletonBlockMedium}`} />
          <div className={`${styles.skeletonBlock} ${styles.skeletonBlockShort}`} />
        </div>
      )}
    </div>
  );
};

export default LoadingState;
