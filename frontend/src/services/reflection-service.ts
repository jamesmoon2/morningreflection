/**
 * Reflection API service
 *
 * Handles all reflection-related API operations including fetching
 * daily reflections, historical reflections, and calendar metadata.
 */

import { apiClient } from './api-client';
import { Reflection, CalendarDay } from '../types';
import { format } from 'date-fns';

/**
 * Get today's reflection
 */
export async function getTodayReflection(): Promise<Reflection> {
  return apiClient.get<Reflection>('/reflections/today');
}

/**
 * Get reflection for a specific date
 */
export async function getReflectionByDate(date: Date | string): Promise<Reflection> {
  const dateStr = typeof date === 'string' ? date : format(date, 'yyyy-MM-dd');
  return apiClient.get<Reflection>(`/reflections/${dateStr}`);
}

/**
 * Get calendar metadata for a month
 * Shows which days have reflections available
 */
export async function getCalendarMetadata(year: number, month: number): Promise<CalendarDay[]> {
  return apiClient.get<CalendarDay[]>('/reflections/calendar', { year, month });
}

/**
 * Get calendar metadata for current month
 */
export async function getCurrentMonthCalendar(): Promise<CalendarDay[]> {
  const now = new Date();
  return getCalendarMetadata(now.getFullYear(), now.getMonth() + 1);
}
