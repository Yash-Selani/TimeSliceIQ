import React, { useState } from 'react';
import styles from './Landing.module.css';

export interface LandingProps {
  onSubmit: (url: string) => void;
  isLoading?: boolean;
  error?: string | null;
  initialUrl?: string;
}

export const Landing: React.FC<LandingProps> = ({
  onSubmit,
  isLoading = false,
  error = null,
  initialUrl = '',
}) => {
  const [url, setUrl] = useState(initialUrl);
  const [localError, setLocalError] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = url.trim();
    if (!trimmed) {
      setLocalError('Please enter a YouTube video URL.');
      return;
    }
    setLocalError(null);
    onSubmit(trimmed);
  };

  const displayedError = error || localError;

  return (
    <main id="main-content" tabIndex={-1} className={styles.container}>
      <div className={styles.content}>
        <h1 className={styles.headline}>TIMESLICEIQ</h1>
        <p className={styles.subhead}>
          Paste a lecture URL to ask questions with millisecond-exact citations.
        </p>

        <form className={styles.form} onSubmit={handleSubmit} noValidate>
          <label htmlFor="landing-url-input" className="sr-only">
            YouTube lecture URL
          </label>
          <div
            className={`${styles.inputGroup} ${
              displayedError ? styles.inputGroupError : ''
            }`}
          >
            <input
              id="landing-url-input"
              type="url"
              className={styles.input}
              placeholder="https://www.youtube.com/watch?v=..."
              value={url}
              onChange={(e) => {
                setUrl(e.target.value);
                if (localError) setLocalError(null);
              }}
              disabled={isLoading}
              autoFocus
              autoComplete="off"
              spellCheck="false"
              aria-invalid={Boolean(displayedError)}
              aria-describedby={displayedError ? 'landing-url-error' : undefined}
            />
            <button
              type="submit"
              className={styles.submitBtn}
              disabled={isLoading || !url.trim()}
              aria-busy={isLoading}
            >
              {isLoading ? 'Indexing...' : 'Index'}
            </button>
          </div>
          {displayedError && (
            <div id="landing-url-error" className={styles.errorText} role="alert">
              {displayedError}
            </div>
          )}
        </form>
      </div>
    </main>
  );
};

export default Landing;
