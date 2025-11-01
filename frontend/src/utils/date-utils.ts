/**
 * Date utility functions
 */

import { format, parseISO, isValid, startOfMonth, endOfMonth, eachDayOfInterval } from 'date-fns';

/**
 * Format date as YYYY-MM-DD
 */
export function formatDateForApi(date: Date): string {
  return format(date, 'yyyy-MM-dd');
}

/**
 * Format date for display (e.g., "Monday, January 1, 2024")
 */
export function formatDateForDisplay(date: Date | string): string {
  const dateObj = typeof date === 'string' ? parseISO(date) : date;
  if (!isValid(dateObj)) {
    return 'Invalid date';
  }
  return format(dateObj, 'EEEE, MMMM d, yyyy');
}

/**
 * Format date as short display (e.g., "Jan 1, 2024")
 */
export function formatDateShort(date: Date | string): string {
  const dateObj = typeof date === 'string' ? parseISO(date) : date;
  if (!isValid(dateObj)) {
    return 'Invalid date';
  }
  return format(dateObj, 'MMM d, yyyy');
}

/**
 * Get all days in a month
 */
export function getDaysInMonth(year: number, month: number): Date[] {
  const start = startOfMonth(new Date(year, month - 1));
  const end = endOfMonth(new Date(year, month - 1));
  return eachDayOfInterval({ start, end });
}

/**
 * Check if a date is today
 */
export function isToday(date: Date | string): boolean {
  const dateObj = typeof date === 'string' ? parseISO(date) : date;
  const today = new Date();
  return formatDateForApi(dateObj) === formatDateForApi(today);
}

/**
 * Parse date string safely
 */
export function parseDateString(dateStr: string): Date | null {
  try {
    const date = parseISO(dateStr);
    return isValid(date) ? date : null;
  } catch {
    return null;
  }
}
