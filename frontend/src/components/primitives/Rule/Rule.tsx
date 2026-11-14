import React from 'react';
import styles from './Rule.module.css';

export type RuleSpacing = 'none' | 'sm' | 'md' | 'lg';

export interface RuleProps extends React.HTMLAttributes<HTMLHRElement> {
  spacing?: RuleSpacing;
  vertical?: boolean;
  className?: string;
}

export const Rule = React.forwardRef<HTMLHRElement, RuleProps>(
  ({ spacing = 'md', vertical = false, className, ...rest }, ref) => {
    const classNames = [
      styles.rule,
      vertical ? styles.vertical : styles.horizontal,
      styles[`spacing-${spacing}`],
      className,
    ]
      .filter(Boolean)
      .join(' ');

    return (
      <hr
        ref={ref}
        role="separator"
        aria-orientation={vertical ? 'vertical' : 'horizontal'}
        className={classNames}
        {...rest}
      />
    );
  },
);

Rule.displayName = 'Rule';
