/**
 * Custom hook for managing journal entries
 */

import { useState, useEffect } from 'react';
import { JournalEntry } from '../types';
import {
  getJournalEntry,
  saveJournalEntry,
  deleteJournalEntry,
} from '../services/journal-service';

export function useJournal(date?: Date | string) {
  const [entry, setEntry] = useState<JournalEntry | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (date) {
      loadEntry();
    } else {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [date]);

  async function loadEntry() {
    if (!date) return;

    try {
      setLoading(true);
      setError(null);

      const data = await getJournalEntry(date);
      setEntry(data);
    } catch (err) {
      // 404 is expected if no entry exists yet
      if ((err as { statusCode?: number }).statusCode === 404) {
        setEntry(null);
      } else {
        setError(err instanceof Error ? err.message : 'Failed to load journal entry');
      }
    } finally {
      setLoading(false);
    }
  }

  async function saveEntry(text: string) {
    if (!date) {
      throw new Error('Date is required to save journal entry');
    }

    try {
      setSaving(true);
      setError(null);

      await saveJournalEntry(date, text);
      await loadEntry(); // Reload to get updated metadata
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save journal entry');
      throw err;
    } finally {
      setSaving(false);
    }
  }

  async function deleteEntry() {
    if (!date) {
      throw new Error('Date is required to delete journal entry');
    }

    try {
      setSaving(true);
      setError(null);

      await deleteJournalEntry(date);
      setEntry(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete journal entry');
      throw err;
    } finally {
      setSaving(false);
    }
  }

  return {
    entry,
    loading,
    error,
    saving,
    saveEntry,
    deleteEntry,
    reload: loadEntry,
  };
}
