/**
 * Calendar Page
 *
 * Browse reflections and journal entries by date
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getCalendarMetadata } from '../services/reflection-service';
import { getJournalList } from '../services/journal-service';
import { Card } from '../components/Card';
import { Loading } from '../components/Loading';
import { formatDateForApi, formatDateShort, getDaysInMonth } from '../utils/date-utils';
import { CalendarDay, JournalListItem } from '../types';
import { format, startOfMonth, getDay } from 'date-fns';

export function CalendarPage() {
  const navigate = useNavigate();
  const [currentDate, setCurrentDate] = useState(new Date());
  const [calendarData, setCalendarData] = useState<CalendarDay[]>([]);
  const [journalData, setJournalData] = useState<Map<string, JournalListItem>>(new Map());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth() + 1;

  useEffect(() => {
    loadCalendarData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [year, month]);

  const loadCalendarData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Load calendar metadata and journal list
      const [calendar, journals] = await Promise.all([
        getCalendarMetadata(year, month),
        getJournalList(),
      ]);

      setCalendarData(calendar);

      // Convert journal list to map for quick lookup
      const journalMap = new Map<string, JournalListItem>();
      journals.forEach((j) => journalMap.set(j.date, j));
      setJournalData(journalMap);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load calendar');
    } finally {
      setLoading(false);
    }
  };

  const handlePreviousMonth = () => {
    setCurrentDate(new Date(year, month - 2, 1));
  };

  const handleNextMonth = () => {
    setCurrentDate(new Date(year, month, 1));
  };

  const handleDateClick = (date: Date) => {
    navigate(`/daily/${formatDateForApi(date)}`);
  };

  const renderCalendar = () => {
    const days = getDaysInMonth(year, month);
    const firstDayOfMonth = startOfMonth(new Date(year, month - 1));
    const startingDayOfWeek = getDay(firstDayOfMonth);

    // Create empty cells for days before the first day of the month
    const emptyCells = Array(startingDayOfWeek).fill(null);

    const allCells = [...emptyCells, ...days];

    return (
      <div className="grid grid-cols-7 gap-2">
        {/* Day headers */}
        {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day) => (
          <div key={day} className="text-center font-semibold text-gray-600 py-2">
            {day}
          </div>
        ))}

        {/* Calendar cells */}
        {allCells.map((date, index) => {
          if (!date) {
            return <div key={`empty-${index}`} className="aspect-square" />;
          }

          const dateStr = formatDateForApi(date);
          const calendarDay = calendarData.find((d) => d.date === dateStr);
          const journal = journalData.get(dateStr);
          const hasReflection = calendarDay?.hasReflection || false;
          const hasJournal = journal !== undefined;
          const isToday = formatDateForApi(new Date()) === dateStr;
          const isFuture = date > new Date();

          return (
            <button
              key={dateStr}
              onClick={() => !isFuture && handleDateClick(date)}
              disabled={isFuture}
              className={`
                aspect-square p-2 rounded-lg border-2 transition-all
                ${isToday ? 'border-primary-500 bg-primary-50' : 'border-gray-200'}
                ${hasReflection || hasJournal ? 'bg-green-50' : 'bg-white'}
                ${isFuture ? 'opacity-40 cursor-not-allowed' : 'hover:border-primary-400 hover:shadow-md cursor-pointer'}
              `}
            >
              <div className="flex flex-col h-full">
                <span className={`text-sm font-semibold ${isToday ? 'text-primary-700' : 'text-gray-800'}`}>
                  {date.getDate()}
                </span>
                <div className="flex-1 flex items-center justify-center gap-1 mt-1">
                  {hasReflection && (
                    <div className="w-2 h-2 rounded-full bg-primary-500" title="Has reflection" />
                  )}
                  {hasJournal && (
                    <div className="w-2 h-2 rounded-full bg-green-500" title="Has journal" />
                  )}
                </div>
                {journal && (
                  <span className="text-xs text-gray-500">{journal.word_count}w</span>
                )}
              </div>
            </button>
          );
        })}
      </div>
    );
  };

  if (loading) {
    return <Loading message="Loading calendar..." />;
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-serif text-stoic-800 mb-2">Calendar</h1>
        <p className="text-gray-600">Browse your reflections and journal entries</p>
      </div>

      {/* Calendar Card */}
      <Card>
        {/* Month Navigation */}
        <div className="flex items-center justify-between mb-6">
          <button
            onClick={handlePreviousMonth}
            className="px-4 py-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
          >
            ← Previous
          </button>
          <h2 className="text-2xl font-serif text-stoic-800">
            {format(currentDate, 'MMMM yyyy')}
          </h2>
          <button
            onClick={handleNextMonth}
            disabled={month >= new Date().getMonth() + 1 && year >= new Date().getFullYear()}
            className="px-4 py-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Next →
          </button>
        </div>

        {/* Error State */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        {/* Calendar Grid */}
        {renderCalendar()}

        {/* Legend */}
        <div className="mt-6 pt-6 border-t border-gray-200">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Legend</h3>
          <div className="flex flex-wrap gap-4 text-sm text-gray-600">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-primary-500" />
              <span>Has reflection</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-green-500" />
              <span>Has journal entry</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 border-2 border-primary-500 bg-primary-50 rounded" />
              <span>Today</span>
            </div>
          </div>
        </div>
      </Card>

      {/* Recent Journal Entries */}
      {journalData.size > 0 && (
        <div className="mt-8">
          <h2 className="text-2xl font-serif text-stoic-800 mb-4">Recent Journal Entries</h2>
          <div className="grid gap-4">
            {Array.from(journalData.entries())
              .slice(0, 5)
              .map(([date, journal]) => (
                <Card
                  key={date}
                  padding="small"
                  className="cursor-pointer hover:shadow-lg transition-shadow"
                  onClick={() => navigate(`/daily/${date}`)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className="font-semibold text-stoic-800 mb-1">
                        {formatDateShort(date)}
                      </h3>
                      <p className="text-sm text-gray-600 line-clamp-2">{journal.preview}</p>
                    </div>
                    <span className="text-xs text-gray-500 ml-4">{journal.word_count} words</span>
                  </div>
                </Card>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
