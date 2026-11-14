import React, { useEffect, useState } from 'react';
import styles from './ErrorState.module.css';
import {
  DEFAULT_ERROR_PRESET,
  ERROR_PRESETS,
  type ErrorCode,
  type ErrorStateProps,
} from './types';

export const ErrorState: React.FC<ErrorStateProps> = ({
  code = 'UNKNOWN_ERROR',
  title,
  description,
  actionLabel,
  onAction,
  onRetry,
  countdownSeconds = 30,
  autoCountdown = true,
  onCountdownComplete,
  technicalDetails,
  className = '',
  style,
}) => {
  const isRateLimited = code === 'RATE_LIMITED';
  const [secondsRemaining, setSecondsRemaining] = useState<number>(countdownSeconds);

  // Sync initial countdown seconds when prop changes
  useEffect(() => {
    setSecondsRemaining(countdownSeconds);
  }, [countdownSeconds]);

  // Rate-limiting countdown timer
  useEffect(() => {
    if (!isRateLimited || !autoCountdown || secondsRemaining <= 0) {
      return;
    }

    const timer = setInterval(() => {
      setSecondsRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          onCountdownComplete?.();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [isRateLimited, autoCountdown, secondsRemaining, onCountdownComplete]);

  // Lookup preset or use fallback
  const preset = (code in ERROR_PRESETS
    ? ERROR_PRESETS[code as ErrorCode]
    : DEFAULT_ERROR_PRESET);

  const displayTitle = title ?? preset.title;
  const displayDescription = description ?? preset.description;
  const defaultActionText = actionLabel ?? preset.actionLabel;

  const isCountingDown = isRateLimited && autoCountdown && secondsRemaining > 0;
  const buttonText = isCountingDown
    ? `Retry in ${secondsRemaining}s`
    : defaultActionText;

  const handleActionClick = () => {
    if (isCountingDown) return;
    if (onAction) {
      onAction();
    } else if (onRetry) {
      onRetry();
    }
  };

  const containerClassName = `${styles.errorContainer} ${className}`.trim();

  return (
    <div
      role="alert"
      aria-live="assertive"
      className={containerClassName}
      style={style}
      data-testid="error-state"
      data-error-code={code}
    >
      <div className={styles.errorMeta}>
        <span className={styles.errorMetaLabel}>ERR // {code}</span>
        <span className={styles.errorMetaTimestamp}>STATUS 5XX / 4XX</span>
      </div>

      <h2 className={styles.errorTitle}>{displayTitle}</h2>

      <hr className={styles.divider} />

      <p className={styles.errorDescription}>{displayDescription}</p>

      {technicalDetails && (
        <pre className={styles.technicalDetails} aria-label="Technical details">
          {technicalDetails}
        </pre>
      )}

      <div className={styles.errorActions}>
        <button
          type="button"
          onClick={handleActionClick}
          disabled={isCountingDown}
          className={styles.actionButton}
          aria-disabled={isCountingDown}
        >
          {buttonText}
        </button>

        {isCountingDown && (
          <span className={styles.timerNotice} aria-live="polite">
            [COOLING DOWN: {secondsRemaining}s]
          </span>
        )}
      </div>
    </div>
  );
};

export default ErrorState;
