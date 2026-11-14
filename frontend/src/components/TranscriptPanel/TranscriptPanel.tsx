import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import type { TranscriptLine } from '@/types/api';
import { usePlayerContext } from '@/contexts/PlayerContext';
import { secondsToLabel } from '@/lib/format';
import { findActiveTranscriptIndex } from './transcriptUtils';
import styles from './TranscriptPanel.module.css';

export interface TranscriptPanelProps {
  transcript: TranscriptLine[];
  isActiveTab?: boolean;
}

interface DisplayLineItem {
  line: TranscriptLine;
  originalIndex: number;
}

/**
 * Escapes regex special characters and highlights query matches inside text.
 */
function renderHighlightedText(text: string, query: string): React.ReactNode {
  const trimmed = query.trim();
  if (!trimmed) {
    return text;
  }

  const escaped = trimmed.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const parts = text.split(new RegExp(`(${escaped})`, 'gi'));

  return parts.map((part, index) =>
    part.toLowerCase() === trimmed.toLowerCase() ? (
      <mark key={index} className={styles.highlight}>
        {part}
      </mark>
    ) : (
      part
    ),
  );
}

export const TranscriptPanel: React.FC<TranscriptPanelProps> = ({
  transcript,
  isActiveTab = true,
}) => {
  const { currentTime, seekTo } = usePlayerContext();

  const [searchQuery, setSearchQuery] = useState('');
  const [autoScroll, setAutoScroll] = useState(true);

  const lineRefs = useRef<Map<number, HTMLButtonElement>>(new Map());
  const listContainerRef = useRef<HTMLUListElement | null>(null);

  // Active line index in the full (unfiltered) transcript
  const activeIndex = useMemo(() => {
    return findActiveTranscriptIndex(transcript, currentTime);
  }, [transcript, currentTime]);

  // Filtered transcript lines based on real-time case-insensitive search
  const filteredLines = useMemo<DisplayLineItem[]>(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) {
      return transcript.map((line, originalIndex) => ({ line, originalIndex }));
    }
    return transcript
      .map((line, originalIndex) => ({ line, originalIndex }))
      .filter(({ line }) => line.text.toLowerCase().includes(query));
  }, [transcript, searchQuery]);

  // Scroll a specific line into view smoothly
  const scrollToLine = useCallback((index: number, smooth: boolean = true) => {
    const element = lineRefs.current.get(index);
    if (!element) return;

    const prefersReducedMotion =
      typeof window !== 'undefined' &&
      window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

    const behavior: ScrollBehavior = !smooth || prefersReducedMotion ? 'auto' : 'smooth';
    element.scrollIntoView({ behavior, block: 'center' });
  }, []);

  // Auto-scroll when active line changes and autoScroll is enabled
  useEffect(() => {
    if (!autoScroll) return;
    if (!isActiveTab) return;
    if (activeIndex < 0) return;

    scrollToLine(activeIndex, true);
  }, [activeIndex, autoScroll, isActiveTab, scrollToLine]);

  // Listen to custom DOM event 'timesliceiq:seek' to scroll immediately
  useEffect(() => {
    const handleCustomSeek = (event: Event) => {
      const customEvent = event as CustomEvent<{ seconds?: number }>;
      const seconds = customEvent.detail?.seconds;
      if (typeof seconds === 'number') {
        const targetIndex = findActiveTranscriptIndex(transcript, seconds);
        if (targetIndex >= 0 && isActiveTab) {
          scrollToLine(targetIndex, true);
        }
      }
    };

    window.addEventListener('timesliceiq:seek', handleCustomSeek);
    return () => {
      window.removeEventListener('timesliceiq:seek', handleCustomSeek);
    };
  }, [transcript, isActiveTab, scrollToLine]);

  // When tab becomes active, center on the current active line
  useEffect(() => {
    if (isActiveTab && autoScroll && activeIndex >= 0) {
      scrollToLine(activeIndex, false);
    }
  }, [isActiveTab, autoScroll, activeIndex, scrollToLine]);

  const handleLineClick = useCallback(
    (start_s: number) => {
      seekTo(start_s, true);
    },
    [seekTo],
  );

  const toggleAutoScroll = useCallback(() => {
    setAutoScroll((prev) => {
      const next = !prev;
      if (next && activeIndex >= 0) {
        scrollToLine(activeIndex, true);
      }
      return next;
    });
  }, [activeIndex, scrollToLine]);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
  };

  const handleClearSearch = () => {
    setSearchQuery('');
  };

  return (
    <section className={styles.container} aria-label="Transcript" data-testid="transcript-panel">
      {/* Panel Header */}
      <div className={styles.header}>
        <div className={styles.headerTop}>
          <span className={styles.microLabel}>03 · TRANSCRIPT</span>
          <button
            type="button"
            className={styles.autoScrollButton}
            onClick={toggleAutoScroll}
            aria-pressed={autoScroll}
            title={autoScroll ? 'Disable automatic scrolling' : 'Enable automatic scrolling'}
          >
            <span
              className={`${styles.statusIndicator} ${
                autoScroll ? styles.statusIndicatorActive : ''
              }`}
              aria-hidden="true"
            />
            <span>Auto-scroll: {autoScroll ? 'ON' : 'OFF'}</span>
          </button>
        </div>

        {/* Real-time search filter input */}
        <div className={styles.searchWrapper}>
          <input
            type="text"
            className={styles.searchInput}
            placeholder="Search transcript..."
            value={searchQuery}
            onChange={handleSearchChange}
            aria-label="Filter transcript by text"
          />
          {searchQuery && (
            <button
              type="button"
              className={styles.clearButton}
              onClick={handleClearSearch}
              aria-label="Clear search query"
              title="Clear search"
            >
              ×
            </button>
          )}
        </div>

        {searchQuery.trim() && (
          <div
            className={styles.searchMeta}
            role="status"
            aria-live="polite"
            aria-atomic="true"
          >
            <span>
              {filteredLines.length} {filteredLines.length === 1 ? 'match' : 'matches'}
            </span>
            <span>{transcript.length} total lines</span>
          </div>
        )}
      </div>

      {/* Transcript List */}
      {transcript.length === 0 ? (
        <div className={styles.emptyState}>
          <p className={styles.emptyHeadline}>No transcript available</p>
          <p>Captions for this lecture could not be loaded.</p>
        </div>
      ) : filteredLines.length === 0 ? (
        <div className={styles.emptyState}>
          <p className={styles.emptyHeadline}>No matches found</p>
          <p>Try searching for a different keyword or timestamp.</p>
        </div>
      ) : (
        <ul
          ref={listContainerRef}
          className={styles.transcriptList}
          aria-label="Video transcript lines"
        >
          {filteredLines.map(({ line, originalIndex }) => {
            const isActive = originalIndex === activeIndex;
            const timeLabel = secondsToLabel(line.start_s);

            return (
              <li key={`${originalIndex}-${line.start_s}`}>
                <button
                  type="button"
                  ref={(el) => {
                    if (el) {
                      lineRefs.current.set(originalIndex, el);
                    } else {
                      lineRefs.current.delete(originalIndex);
                    }
                  }}
                  className={`${styles.lineItem} ${isActive ? styles.activeLine : ''}`}
                  onClick={() => handleLineClick(line.start_s)}
                  aria-current={isActive ? 'time' : undefined}
                  aria-label={`${timeLabel}: ${line.text}`}
                >
                  <span
                    className={`${styles.timestampBadge} ${
                      isActive ? styles.activeTimestamp : ''
                    }`}
                  >
                    {timeLabel}
                  </span>
                  <span className={styles.lineText}>
                    {renderHighlightedText(line.text, searchQuery)}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
};

export default TranscriptPanel;
