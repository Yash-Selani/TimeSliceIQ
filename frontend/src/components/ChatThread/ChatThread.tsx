import React, { useRef, useEffect } from 'react';
import { Button } from '@/components/primitives/Button';
import { Skeleton } from '@/components/primitives/Skeleton';
import { TimestampChip } from '@/components/TimestampChip';
import { ChatComposer } from '@/components/ChatComposer';
import type { AnswerBlock, Citation } from '@/types/api';
import styles from './ChatThread.module.css';

export interface ChatMessageItem {
  id?: string;
  role: 'user' | 'assistant';
  content?: string;
  blocks?: AnswerBlock[];
  follow_ups?: string[];
  timestamp?: number;
}

export interface ChatThreadProps {
  messages: ChatMessageItem[];
  isLoading?: boolean;
  error?: string | Error | null;
  onSendMessage?: (question: string) => void;
  onRetry?: () => void;
  onSelectFollowUp?: (question: string) => void;
  className?: string;
  placeholder?: string;
  hideComposer?: boolean;
}

export const ChatThread: React.FC<ChatThreadProps> = ({
  messages,
  isLoading = false,
  error = null,
  onSendMessage,
  onRetry,
  onSelectFollowUp,
  className,
  placeholder,
  hideComposer = false,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (typeof bottomRef.current?.scrollIntoView === 'function') {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isLoading, error]);

  const handleFollowUpClick = (suggestion: string) => {
    if (onSelectFollowUp) {
      onSelectFollowUp(suggestion);
    } else if (onSendMessage) {
      onSendMessage(suggestion);
    }
  };

  const getErrorMessage = (err: string | Error | null): string => {
    if (!err) return '';
    return typeof err === 'string' ? err : err.message || 'An error occurred while answering.';
  };

  return (
    <section
      className={[styles.container, className].filter(Boolean).join(' ')}
      aria-label="Discussion Thread"
    >
      <header className={styles.header}>
        <span className={styles.microLabel}>02 · CHAT</span>
      </header>

      <div
        className={styles.messageList}
        aria-live="polite"
        aria-relevant="additions text"
        role="log"
        aria-label="Chat messages"
      >
        {messages.length === 0 && !isLoading && (
          <div className={styles.emptyState}>
            <p className={styles.emptyTitle}>NO QUESTIONS YET</p>
            <p className={styles.emptySubtitle}>
              Ask any question about this lecture. Answers cite exact timestamps in the video.
            </p>
          </div>
        )}

        {messages.map((message, index) => {
          const isUser = message.role === 'user';
          const label = isUser ? 'YOU' : 'TIMESLICEIQ';

          return (
            <article
              key={message.id || `${message.role}-${index}`}
              className={styles.messageItem}
            >
              <div className={styles.messageHeader}>
                <span
                  className={[
                    styles.roleLabel,
                    !isUser ? styles.roleLabelAssistant : '',
                  ]
                    .filter(Boolean)
                    .join(' ')}
                >
                  {label}
                </span>
              </div>

              {isUser ? (
                <div className={styles.userText}>{message.content}</div>
              ) : (
                <div className={styles.assistantContent}>
                  {message.blocks && message.blocks.length > 0 ? (
                    message.blocks.map((block: AnswerBlock, bIdx: number) => (
                      <div key={bIdx} className={styles.claimBlock}>
                        <span className={styles.plainText}>{block.text}</span>
                        {block.cites && block.cites.length > 0 && (
                          <span className={styles.citationsGroup}>
                            {block.cites.map((cite: Citation, cIdx: number) => (
                              <TimestampChip
                                key={`${cite.chunk_id || cite.seconds}-${cIdx}`}
                                seconds={cite.seconds}
                                label={cite.label}
                              />
                            ))}
                          </span>
                        )}
                      </div>
                    ))
                  ) : message.content ? (
                    <div className={styles.plainText}>{message.content}</div>
                  ) : null}

                  {message.follow_ups && message.follow_ups.length > 0 && (
                    <div className={styles.followUpsContainer}>
                      <span className={styles.followUpsTitle}>FOLLOW-UP SUGGESTIONS</span>
                      <div className={styles.followUpButtons}>
                        {message.follow_ups.map((suggestion, sIdx) => (
                          <Button
                            key={sIdx}
                            variant="ghost"
                            size="sm"
                            onClick={() => handleFollowUpClick(suggestion)}
                            className={styles.followUpButton}
                          >
                            {suggestion}
                          </Button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </article>
          );
        })}

        {isLoading && (
          <article className={styles.messageItem} aria-busy="true">
            <div className={styles.messageHeader}>
              <span className={[styles.roleLabel, styles.roleLabelAssistant].join(' ')}>
                TIMESLICEIQ
              </span>
            </div>
            <div className={styles.loadingContainer}>
              <Skeleton lines={3} />
            </div>
          </article>
        )}

        {error && (
          <div className={styles.errorBanner} role="alert">
            <div className={styles.errorContent}>
              <span className={styles.errorLabel}>ERROR:</span>
              <span className={styles.errorMessageText}>{getErrorMessage(error)}</span>
            </div>
            {onRetry && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onRetry}
                className={styles.retryButton}
              >
                Retry
              </Button>
            )}
          </div>
        )}

        <div ref={bottomRef} tabIndex={-1} aria-hidden="true" />
      </div>

      {!hideComposer && onSendMessage && (
        <div className={styles.composerWrapper}>
          <ChatComposer
            onSend={onSendMessage}
            disabled={isLoading}
            placeholder={placeholder}
          />
        </div>
      )}
    </section>
  );
};

export default ChatThread;
