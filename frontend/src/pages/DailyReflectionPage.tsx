/**
 * Daily Reflection Page
 *
 * View a specific day's reflection and journal entry.
 * Handles magic link tokens from emails.
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useReflection } from '../hooks/useReflection';
import { useJournal } from '../hooks/useJournal';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { Loading } from '../components/Loading';
import { formatDateForDisplay, parseDateString } from '../utils/date-utils';
import { validateMagicLink } from '../utils/magic-link';

export function DailyReflectionPage() {
  const { date } = useParams<{ date: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { isAuthenticated, login } = useAuth();

  const token = searchParams.get('token');
  const [magicLinkError, setMagicLinkError] = useState<string | null>(null);
  const [processingMagicLink, setProcessingMagicLink] = useState(!!token);

  const dateObj = date ? parseDateString(date) : null;
  const { reflection, loading: reflectionLoading, error: reflectionError } = useReflection(date);
  const {
    entry,
    loading: journalLoading,
    saving,
    saveEntry,
  } = useJournal(date);

  const [journalText, setJournalText] = useState('');
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Handle magic link token
  useEffect(() => {
    if (token && !isAuthenticated) {
      handleMagicLink(token);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, isAuthenticated]);

  const handleMagicLink = async (linkToken: string) => {
    try {
      setProcessingMagicLink(true);

      // Validate token structure
      const validation = validateMagicLink(linkToken);
      if (!validation.valid) {
        setMagicLinkError(validation.error || 'Invalid magic link');
        return;
      }

      // In a production app, you might want to verify the token with the backend
      // and automatically sign the user in. For now, we'll just show a message.
      setMagicLinkError(null);

      // Redirect to login if not authenticated
      if (!isAuthenticated) {
        navigate('/login', {
          state: {
            message: 'Please sign in to view your reflection.',
            redirectTo: `/daily/${date}`,
          },
        });
      }
    } catch (error) {
      console.error('Magic link error:', error);
      setMagicLinkError('Failed to process magic link. Please sign in manually.');
    } finally {
      setProcessingMagicLink(false);
    }
  };

  // Initialize journal text from existing entry
  useEffect(() => {
    if (entry && !journalText) {
      setJournalText(entry.entry);
    }
  }, [entry, journalText]);

  const handleSaveJournal = async () => {
    if (!journalText.trim()) {
      return;
    }

    try {
      await saveEntry(journalText);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (error) {
      console.error('Failed to save journal:', error);
    }
  };

  const wordCount = journalText.trim().split(/\s+/).filter(Boolean).length;

  // Require authentication
  if (!isAuthenticated && !processingMagicLink) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center">
        <Card>
          <h2 className="text-2xl font-serif text-stoic-800 mb-4">Sign In Required</h2>
          <p className="text-gray-600 mb-6">
            Please sign in to view reflections and journal entries.
          </p>
          <Button onClick={() => navigate('/login')}>Sign In</Button>
        </Card>
      </div>
    );
  }

  if (processingMagicLink) {
    return <Loading message="Processing your magic link..." />;
  }

  if (!dateObj) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center">
        <Card>
          <h2 className="text-2xl font-serif text-stoic-800 mb-4">Invalid Date</h2>
          <p className="text-gray-600 mb-6">The date format is invalid.</p>
          <Button onClick={() => navigate('/calendar')}>Go to Calendar</Button>
        </Card>
      </div>
    );
  }

  if (reflectionLoading || journalLoading) {
    return <Loading message="Loading reflection..." />;
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-serif text-stoic-800 mb-2">
            {formatDateForDisplay(dateObj)}
          </h1>
          <Button variant="secondary" onClick={() => navigate('/calendar')}>
            ← Back to Calendar
          </Button>
        </div>
      </div>

      {/* Magic Link Error */}
      {magicLinkError && (
        <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <p className="text-sm text-yellow-800">{magicLinkError}</p>
        </div>
      )}

      {/* Reflection Card */}
      <Card className="mb-8">
        {reflectionError ? (
          <div className="text-center py-8">
            <p className="text-red-600 mb-4">{reflectionError}</p>
            <p className="text-gray-600">
              No reflection available for this date.
            </p>
          </div>
        ) : reflection ? (
          <>
            <div className="mb-6">
              <h2 className="text-sm font-semibold text-primary-600 uppercase tracking-wide mb-2">
                {reflection.theme}
              </h2>
              <blockquote className="text-xl font-serif text-stoic-800 italic mb-2 border-l-4 border-primary-500 pl-4">
                "{reflection.quote}"
              </blockquote>
              <p className="text-gray-600 text-sm">— {reflection.attribution}</p>
            </div>

            <div className="prose max-w-none mb-6">
              <h3 className="text-lg font-semibold text-stoic-800 mb-3">Reflection</h3>
              <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
                {reflection.reflection}
              </p>
            </div>

            {reflection.journaling_prompt && (
              <div className="bg-amber-50 border-l-4 border-amber-400 p-4 rounded">
                <h3 className="text-sm font-semibold text-amber-900 mb-2">
                  Journaling Prompt
                </h3>
                <p className="text-amber-800">{reflection.journaling_prompt}</p>
              </div>
            )}
          </>
        ) : (
          <div className="text-center py-8">
            <p className="text-gray-600">No reflection available for this date.</p>
          </div>
        )}
      </Card>

      {/* Journal Entry Card */}
      <Card>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-stoic-800">Your Journal Entry</h2>
          <span className="text-sm text-gray-500">
            {wordCount} {wordCount === 1 ? 'word' : 'words'}
          </span>
        </div>

        <textarea
          value={journalText}
          onChange={(e) => setJournalText(e.target.value)}
          placeholder="Write your thoughts, reflections, and insights here..."
          className="w-full h-64 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
          maxLength={10000}
        />

        <div className="mt-4 flex items-center justify-between">
          <div>
            {saveSuccess && (
              <span className="text-sm text-green-600 font-semibold">
                ✓ Saved successfully!
              </span>
            )}
          </div>

          <Button
            onClick={handleSaveJournal}
            isLoading={saving}
            disabled={!journalText.trim()}
          >
            Save Journal
          </Button>
        </div>

        {entry && (
          <p className="mt-3 text-xs text-gray-500">
            Last updated: {new Date(entry.updated_at).toLocaleString()}
          </p>
        )}
      </Card>
    </div>
  );
}
