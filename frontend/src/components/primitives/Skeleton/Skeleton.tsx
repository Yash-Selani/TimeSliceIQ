import React from 'react';
import styles from './Skeleton.module.css';

export interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  lines?: number;
  className?: string;
  style?: React.CSSProperties;
}

function normalizeDimension(value?: string | number): string | undefined {
  if (value === undefined) return undefined;
  return typeof value === 'number' ? `${value}px` : value;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  width,
  height,
  lines,
  className,
  style,
}) => {
  const normWidth = normalizeDimension(width);
  const normHeight = normalizeDimension(height);

  if (lines !== undefined && lines > 1) {
    return (
      <div
        aria-hidden="true"
        className={[styles.linesContainer, className].filter(Boolean).join(' ')}
        style={style}
      >
        {Array.from({ length: lines }).map((_, index) => {
          const isLast = index === lines - 1;
          const lineWidth = normWidth ?? (isLast ? '75%' : '100%');
          const lineHeight = normHeight ?? '16px';
          return (
            <div
              key={index}
              className={styles.block}
              style={{
                width: lineWidth,
                height: lineHeight,
              }}
            />
          );
        })}
      </div>
    );
  }

  return (
    <div
      aria-hidden="true"
      className={[styles.block, className].filter(Boolean).join(' ')}
      style={{
        width: normWidth ?? '100%',
        height: normHeight ?? '20px',
        ...style,
      }}
    />
  );
};
