/**
 * Custom hook for fetching and managing reflections
 */

import { useState, useEffect } from 'react';
import { Reflection } from '../types';
import { getTodayReflection, getReflectionByDate } from '../services/reflection-service';

export function useReflection(date?: Date | string) {
  const [reflection, setReflection] = useState<Reflection | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadReflection();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [date]);

  async function loadReflection() {
    try {
      setLoading(true);
      setError(null);

      const data = date ? await getReflectionByDate(date) : await getTodayReflection();
      setReflection(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load reflection');
      setReflection(null);
    } finally {
      setLoading(false);
    }
  }

  return { reflection, loading, error, reload: loadReflection };
}
