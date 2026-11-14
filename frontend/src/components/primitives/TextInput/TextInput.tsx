import React, { useId } from 'react';
import styles from './TextInput.module.css';

export interface TextInputProps {
  label?: string;
  error?: string;
  placeholder?: string;
  value?: string;
  defaultValue?: string;
  onChange?: (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => void;
  onKeyDown?: (event: React.KeyboardEvent<HTMLInputElement | HTMLTextAreaElement>) => void;
  onBlur?: (event: React.FocusEvent<HTMLInputElement | HTMLTextAreaElement>) => void;
  onFocus?: (event: React.FocusEvent<HTMLInputElement | HTMLTextAreaElement>) => void;
  disabled?: boolean;
  autoFocus?: boolean;
  ariaLabel?: string;
  multiline?: boolean;
  rows?: number;
  id?: string;
  name?: string;
  type?: string;
  className?: string;
  inputClassName?: string;
  autoComplete?: string;
  maxLength?: number;
  readOnly?: boolean;
  required?: boolean;
}

export const TextInput = React.forwardRef<
  HTMLInputElement | HTMLTextAreaElement,
  TextInputProps
>(
  (
    {
      label,
      error,
      placeholder,
      value,
      defaultValue,
      onChange,
      onKeyDown,
      onBlur,
      onFocus,
      disabled = false,
      autoFocus = false,
      ariaLabel,
      multiline = false,
      rows = 3,
      id: customId,
      name,
      type = 'text',
      className,
      inputClassName,
      autoComplete,
      maxLength,
      readOnly = false,
      required = false,
    },
    ref,
  ) => {
    const generatedId = useId();
    const inputId = customId || generatedId;
    const errorId = error ? `${inputId}-error` : undefined;

    const inputClasses = [
      styles.input,
      multiline && styles.textarea,
      error && styles.hasError,
      inputClassName,
    ]
      .filter(Boolean)
      .join(' ');

    const commonProps = {
      id: inputId,
      name,
      value,
      defaultValue,
      placeholder,
      disabled,
      autoFocus,
      readOnly,
      required,
      autoComplete,
      maxLength,
      'aria-label': ariaLabel,
      'aria-invalid': error ? (true as const) : undefined,
      'aria-describedby': errorId,
      className: inputClasses,
      onBlur,
      onFocus,
    };

    return (
      <div className={[styles.wrapper, className].filter(Boolean).join(' ')}>
        {label && (
          <label htmlFor={inputId} className={styles.label}>
            {label}
          </label>
        )}
        {multiline ? (
          <textarea
            ref={ref as React.ForwardedRef<HTMLTextAreaElement>}
            rows={rows}
            onChange={onChange}
            onKeyDown={onKeyDown}
            {...commonProps}
          />
        ) : (
          <input
            ref={ref as React.ForwardedRef<HTMLInputElement>}
            type={type}
            onChange={onChange}
            onKeyDown={onKeyDown}
            {...commonProps}
          />
        )}
        {error && (
          <span id={errorId} role="alert" className={styles.error}>
            {error}
          </span>
        )}
      </div>
    );
  },
);

TextInput.displayName = 'TextInput';
