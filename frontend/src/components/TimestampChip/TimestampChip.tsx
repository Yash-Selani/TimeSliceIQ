import type { ButtonHTMLAttributes, MouseEvent, ReactNode } from 'react';
import { forwardRef, useCallback } from 'react';
import { usePlayerContext } from '@/contexts/PlayerContext';
import { Chip } from '@/components/primitives/Chip';
import { secondsToLabel, secondsToSpoken } from '@/lib/format';
import styles from './TimestampChip.module.css';

export interface TimestampChipProps
  extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'onClick'> {
  /**
   * Video timestamp in seconds to seek to.
   */
  seconds: number;
  /**
   * Optional custom label. Defaults to `secondsToLabel(seconds)` (e.g. "01:15" or "01:01:05").
   */
  label?: string;
  /**
   * Whether this chip is actively playing or selected.
   */
  active?: boolean;
  /**
   * Custom accessible label. Defaults to `Jump to ${secondsToSpoken(seconds)}`.
   */
  ariaLabel?: string;
  /**
   * Optional click handler invoked before seeking.
   */
  onClick?: (event: MouseEvent<HTMLButtonElement>) => void;
  /**
   * Custom children to render instead of the default formatted time label.
   */
  children?: ReactNode;
}

/**
 * TimestampChip displays video timestamps and controls playback via PlayerContext.
 *
 * Visual spec:
 * - Rectangular, 1px accent border, accent text, tabular-nums.
 * - Hover/focus: accent fill with --accent-ink text.
 * - Min tap target: 24x24px.
 * - aria-label: "Jump to ${secondsToSpoken(seconds)}"
 *
 * Interaction:
 * - On click, calls seekTo(seconds, true).
 * - Dispatches custom DOM event 'timesliceiq:seek' on window with { detail: { seconds } }
 *   so TranscriptPanel can scroll to and highlight the active line.
 */
export const TimestampChip = forwardRef<HTMLButtonElement, TimestampChipProps>(
  (
    {
      seconds,
      label,
      active = false,
      ariaLabel,
      onClick,
      children,
      className,
      type = 'button',
      ...rest
    },
    ref,
  ) => {
    const { seekTo } = usePlayerContext();
    const displayLabel = label ?? secondsToLabel(seconds);
    const computedAriaLabel = ariaLabel ?? `Jump to ${secondsToSpoken(seconds)}`;

    const handleClick = useCallback(
      (event: MouseEvent<HTMLButtonElement>) => {
        onClick?.(event);
        if (event.defaultPrevented) {
          return;
        }

        if (seekTo) {
          seekTo(seconds, true);
        }

        if (typeof window !== 'undefined') {
          window.dispatchEvent(
            new CustomEvent('timesliceiq:seek', {
              detail: { seconds },
              bubbles: true,
              cancelable: true,
            }),
          );
        }
      },
      [onClick, seekTo, seconds],
    );

    if (Chip) {
      return (
        <Chip
          ref={ref}
          seconds={seconds}
          label={displayLabel}
          ariaLabel={computedAriaLabel}
          active={active}
          onClick={handleClick}
          className={[styles.timestampChip, className].filter(Boolean).join(' ')}
          type={type}
          {...rest}
        >
          {children ?? displayLabel}
        </Chip>
      );
    }

    return (
      <button
        ref={ref}
        type={type}
        className={[styles.timestampChip, active && styles.active, className]
          .filter(Boolean)
          .join(' ')}
        onClick={handleClick}
        aria-label={computedAriaLabel}
        aria-pressed={active}
        data-seconds={seconds}
        {...rest}
      >
        {children ?? displayLabel}
      </button>
    );
  },
);

TimestampChip.displayName = 'TimestampChip';

export default TimestampChip;
