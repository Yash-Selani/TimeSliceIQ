import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Button } from '@/components/primitives/Button';
import styles from './ChatComposer.module.css';

export interface ChatComposerProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
  maxLength?: number;
  className?: string;
  autoFocus?: boolean;
}

export const ChatComposer: React.FC<ChatComposerProps> = ({
  onSend,
  disabled = false,
  placeholder = 'Ask a question about this lecture (e.g. "What is backpropagation?")...',
  maxLength = 2000,
  className,
  autoFocus = false,
}) => {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const resizeTextarea = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    const nextHeight = Math.min(el.scrollHeight, 160);
    el.style.height = `${Math.max(nextHeight, 48)}px`;
  }, []);

  useEffect(() => {
    resizeTextarea();
  }, [value, resizeTextarea]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) {
      e.preventDefault();
    }
    const trimmed = value.trim();
    if (!trimmed || disabled) return;

    onSend(trimmed);
    setValue('');

    if (textareaRef.current) {
      textareaRef.current.style.height = '48px';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const nextVal = e.target.value;
    if (nextVal.length <= maxLength) {
      setValue(nextVal);
    }
  };

  const charCount = value.length;
  const isNearLimit = charCount >= maxLength * 0.9 && charCount < maxLength;
  const isAtLimit = charCount >= maxLength;

  const counterClass = [
    styles.counter,
    isNearLimit ? styles.counterWarn : '',
    isAtLimit ? styles.counterLimit : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div className={[styles.composerContainer, className].filter(Boolean).join(' ')}>
      <form onSubmit={handleSubmit} className={styles.form} noValidate>
        <div className={styles.inputWrapper}>
          <textarea
            ref={textareaRef}
            value={value}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder={placeholder}
            rows={1}
            maxLength={maxLength}
            autoFocus={autoFocus}
            aria-label="Ask a question"
            className={styles.textarea}
          />
        </div>

        <div className={styles.footer}>
          <span
            className={counterClass}
            aria-live="polite"
            aria-atomic="true"
            aria-label={`${charCount} of ${maxLength} characters used`}
          >
            {`${charCount} / ${maxLength}`}
          </span>

          <div className={styles.actions}>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              disabled={disabled || !value.trim()}
              className={styles.sendButton}
              aria-label="Send question"
            >
              Ask
            </Button>
          </div>
        </div>
      </form>
    </div>
  );
};

export default ChatComposer;
