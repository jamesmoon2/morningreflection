/**
 * Journal API service
 *
 * Handles all journal-related API operations including creating,
 * reading, updating, and deleting journal entries.
 */

import { apiClient } from './api-client';
import { JournalEntry, JournalListItem } from '../types';
import { format } from 'date-fns';

/**
 * Create or update a journal entry for a specific date
 */
export async function saveJournalEntry(date: Date | string, entry: string): Promise<{ message: string }> {
  const dateStr = typeof date === 'string' ? date : format(date, 'yyyy-MM-dd');
  return apiClient.post<{ message: string }>('/journal', {
    date: dateStr,
    entry,
  });
}

/**
 * Get journal entry for a specific date
 */
export async function getJournalEntry(date: Date | string): Promise<JournalEntry> {
  const dateStr = typeof date === 'string' ? date : format(date, 'yyyy-MM-dd');
  return apiClient.get<JournalEntry>(`/journal/${dateStr}`);
}

/**
 * Delete journal entry for a specific date
 */
export async function deleteJournalEntry(date: Date | string): Promise<{ message: string }> {
  const dateStr = typeof date === 'string' ? date : format(date, 'yyyy-MM-dd');
  return apiClient.delete<{ message: string }>(`/journal/${dateStr}`);
}

/**
 * Get list of all journal entries (metadata only)
 */
export async function getJournalList(limit?: number): Promise<JournalListItem[]> {
  return apiClient.get<JournalListItem[]>('/journal/list', limit ? { limit } : undefined);
}

/**
 * Get journal entry for today
 */
export async function getTodayJournalEntry(): Promise<JournalEntry | null> {
  try {
    return await getJournalEntry(new Date());
  } catch (error) {
    // If no entry exists for today, return null
    if ((error as { statusCode?: number }).statusCode === 404) {
      return null;
    }
    throw error;
  }
}
