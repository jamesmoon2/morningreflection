/**
 * Dashboard Page
 *
 * Main landing page showing today's reflection and journal entry
 */

import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useReflection } from '../hooks/useReflection';
import { useJournal } from '../hooks/useJournal';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { Loading } from '../components/Loading';
import { formatDateForDisplay, formatDateForApi } from '../utils/date-utils';

export function DashboardPage() {
  const today = new Date();
  const { reflection, loading: reflectionLoading, error: reflectionError } = useReflection();
  const {
    entry,
    loading: journalLoading,
    error: journalError,
    saving,
    saveEntry,
  } = useJournal(formatDateForApi(today));

  const [journalText, setJournalText] = useState('');
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Initialize journal text from existing entry
  React.useEffect(() => {
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

  if (reflectionLoading || journalLoading) {
    return <Loading message="Loading your daily reflection..." />;
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-serif text-stoic-800 mb-2">
          {formatDateForDisplay(today)}
        </h1>
        <p className="text-gray-600">Your daily reflection and journal</p>
      </div>

      {/* Reflection Card */}
      <Card className="mb-8">
        {reflectionError ? (
          <div className="text-center py-8">
            <p className="text-red-600 mb-4">{reflectionError}</p>
            <p className="text-gray-600">
              Today's reflection may not be available yet. Check back later!
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
            <p className="text-gray-600">No reflection available for today.</p>
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
            {journalError && (
              <span className="text-sm text-red-600">{journalError}</span>
            )}
          </div>

          <div className="flex gap-2">
            <Link to="/calendar">
              <Button variant="secondary">View Calendar</Button>
            </Link>
            <Button
              onClick={handleSaveJournal}
              isLoading={saving}
              disabled={!journalText.trim()}
            >
              Save Journal
            </Button>
          </div>
        </div>

        {entry && (
          <p className="mt-3 text-xs text-gray-500">
            Last updated: {new Date(entry.updated_at).toLocaleString()}
          </p>
        )}
      </Card>

      {/* Quick Links */}
      <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link to="/calendar" className="p-4 bg-white rounded-lg shadow hover:shadow-md transition-shadow">
          <h3 className="font-semibold text-stoic-800 mb-1">Calendar</h3>
          <p className="text-sm text-gray-600">View past reflections and entries</p>
        </Link>
        <Link to="/settings" className="p-4 bg-white rounded-lg shadow hover:shadow-md transition-shadow">
          <h3 className="font-semibold text-stoic-800 mb-1">Settings</h3>
          <p className="text-sm text-gray-600">Manage your preferences</p>
        </Link>
        <a href="#" className="p-4 bg-white rounded-lg shadow hover:shadow-md transition-shadow">
          <h3 className="font-semibold text-stoic-800 mb-1">About</h3>
          <p className="text-sm text-gray-600">Learn more about Morning Reflection</p>
        </a>
      </div>
    </div>
  );
}
