import React, { useState, useMemo } from 'react';
import { UserMenu } from '../Auth/UserMenu';
import styles from './Landing.module.css';

export interface LandingProps {
  onSubmit: (url: string) => void;
  isLoading?: boolean;
  error?: string | null;
  initialUrl?: string;
}

function extractYouTubeId(rawUrl: string): string | null {
  const regExp = /(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))([\w-]{11})/;
  const match = rawUrl.match(regExp);
  return match ? match[1] : null;
}

export const Landing: React.FC<LandingProps> = ({
  onSubmit,
  isLoading = false,
  error = null,
  initialUrl = '',
}) => {
  const [url, setUrl] = useState(initialUrl);
  const [localError, setLocalError] = useState<string | null>(null);

  const detectedVideoId = useMemo(() => extractYouTubeId(url.trim()), [url]);

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
    <>
      <header className={styles.topBar}>
        <span className={styles.wordmark}>TIMESLICEIQ</span>
        <UserMenu onSelectVideo={onSubmit} />
      </header>

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

          {detectedVideoId && (
            <div className={styles.previewBox}>
              <div className={styles.previewHeader}>
                <span className={styles.previewBadge}>DIRECT VIDEO PREVIEW</span>
                <span className={styles.previewId}>ID: {detectedVideoId}</span>
              </div>
              <div className={styles.aspectRatioBox}>
                <iframe
                  src={`https://www.youtube-nocookie.com/embed/${detectedVideoId}?enablejsapi=1&origin=${encodeURIComponent(typeof window !== 'undefined' ? window.location.origin : '')}`}
                  title="YouTube Video Preview"
                  className={styles.previewIframe}
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                  allowFullScreen
                />
              </div>
            </div>
          )}
        </div>
      </main>
    </>
  );
};

export default Landing;
