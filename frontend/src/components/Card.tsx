/**
 * Reusable Card component
 */

import React, { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
  padding?: 'none' | 'small' | 'medium' | 'large';
}

export function Card({ children, className = '', padding = 'medium' }: CardProps) {
  const paddingClasses = {
    none: '',
    small: 'p-4',
    medium: 'p-6',
    large: 'p-8',
  };

  return (
    <div className={`bg-white rounded-lg shadow-md ${paddingClasses[padding]} ${className}`}>
      {children}
    </div>
  );
}
