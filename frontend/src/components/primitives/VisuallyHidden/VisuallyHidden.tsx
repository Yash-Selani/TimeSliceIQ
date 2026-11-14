import React from 'react';
import styles from './VisuallyHidden.module.css';

export interface VisuallyHiddenProps extends React.HTMLAttributes<HTMLElement> {
  children?: React.ReactNode;
  as?: React.ElementType;
  className?: string;
}

export const VisuallyHidden: React.FC<VisuallyHiddenProps> = ({
  children,
  as: Component = 'span',
  className,
  ...rest
}) => {
  return (
    <Component
      className={[styles.srOnly, className].filter(Boolean).join(' ')}
      {...rest}
    >
      {children}
    </Component>
  );
};
