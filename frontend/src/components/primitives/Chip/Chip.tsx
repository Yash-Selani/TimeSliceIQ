import React from 'react';
import styles from './Chip.module.css';

function formatTimestamp(totalSeconds: number): string {
  const sec = Math.max(0, Math.floor(totalSeconds));
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  const pad = (n: number) => String(n).padStart(2, '0');
  if (h > 0) {
    return `${pad(h)}:${pad(m)}:${pad(s)}`;
  }
  return `${pad(m)}:${pad(s)}`;
}

export interface ChipProps extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, 'onClick'> {
  label?: string;
  seconds?: number;
  active?: boolean;
  onClick?: (event: React.MouseEvent<HTMLButtonElement>) => void;
  ariaLabel?: string;
  children?: React.ReactNode;
}

export const Chip = React.forwardRef<HTMLButtonElement, ChipProps>(
  (
    {
      label,
      seconds,
      active = false,
      onClick,
      ariaLabel,
      children,
      className,
      disabled = false,
      type = 'button',
      ...rest
    },
    ref,
  ) => {
    const formattedTime = seconds !== undefined ? formatTimestamp(seconds) : undefined;
    const content = children ?? label ?? formattedTime;

    const computedAriaLabel =
      ariaLabel ??
      (typeof content === 'string'
        ? content
        : formattedTime
          ? `Jump to ${formattedTime}`
          : undefined);

    const classNames = [
      styles.chip,
      active && styles.active,
      className,
    ]
      .filter(Boolean)
      .join(' ');

    return (
      <button
        ref={ref}
        type={type}
        className={classNames}
        disabled={disabled}
        onClick={onClick}
        aria-label={computedAriaLabel}
        aria-pressed={active}
        data-seconds={seconds}
        {...rest}
      >
        {content}
      </button>
    );
  },
);

Chip.displayName = 'Chip';
