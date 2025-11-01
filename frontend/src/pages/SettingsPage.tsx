/**
 * Settings Page
 *
 * Manage user preferences and account settings
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { getUserPreferences, updateUserPreferences, deleteUserAccount } from '../services/user-service';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { Input } from '../components/Input';
import { Loading } from '../components/Loading';
import { isValidTime } from '../utils/validation';
import { UserPreferences } from '../types';

export function SettingsPage() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const [preferences, setPreferences] = useState<UserPreferences>({
    email_enabled: true,
    delivery_time: '07:00',
    timezone: 'America/New_York',
  });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    loadPreferences();
  }, []);

  const loadPreferences = async () => {
    try {
      setLoading(true);
      const prefs = await getUserPreferences();
      setPreferences({
        email_enabled: prefs.email_enabled ?? true,
        delivery_time: prefs.delivery_time || '07:00',
        timezone: prefs.timezone || 'America/New_York',
      });
    } catch (err) {
      console.error('Failed to load preferences:', err);
      setError('Failed to load preferences');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setError(null);

    // Validate
    if (preferences.delivery_time && !isValidTime(preferences.delivery_time)) {
      setError('Invalid delivery time format. Use HH:MM (e.g., 07:00)');
      return;
    }

    try {
      setSaving(true);
      await updateUserPreferences(preferences);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      console.error('Failed to save preferences:', err);
      setError(err instanceof Error ? err.message : 'Failed to save preferences');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteAccount = async () => {
    try {
      setDeleting(true);
      await deleteUserAccount();
      await logout();
      navigate('/login', {
        state: { message: 'Your account has been deleted.' }
      });
    } catch (err) {
      console.error('Failed to delete account:', err);
      setError(err instanceof Error ? err.message : 'Failed to delete account');
    } finally {
      setDeleting(false);
      setShowDeleteConfirm(false);
    }
  };

  if (loading) {
    return <Loading message="Loading settings..." />;
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-serif text-stoic-800 mb-2">Settings</h1>
        <p className="text-gray-600">Manage your account and preferences</p>
      </div>

      {/* Account Information */}
      <Card className="mb-6">
        <h2 className="text-xl font-semibold text-stoic-800 mb-4">Account Information</h2>
        <div className="space-y-3">
          <div>
            <label className="text-sm font-medium text-gray-700">Email</label>
            <p className="text-gray-900">{user?.email || 'Not available'}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700">User ID</label>
            <p className="text-gray-500 text-sm font-mono">{user?.user_id || 'Not available'}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700">Member Since</label>
            <p className="text-gray-900">
              {user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'Not available'}
            </p>
          </div>
        </div>
      </Card>

      {/* Email Preferences */}
      <Card className="mb-6">
        <h2 className="text-xl font-semibold text-stoic-800 mb-4">Email Preferences</h2>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        <div className="space-y-4">
          {/* Email Enabled Toggle */}
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">Daily Reflection Emails</label>
              <p className="text-sm text-gray-500">Receive daily reflections via email</p>
            </div>
            <button
              onClick={() => setPreferences({ ...preferences, email_enabled: !preferences.email_enabled })}
              className={`
                relative inline-flex h-6 w-11 items-center rounded-full transition-colors
                ${preferences.email_enabled ? 'bg-primary-600' : 'bg-gray-200'}
              `}
            >
              <span
                className={`
                  inline-block h-4 w-4 transform rounded-full bg-white transition-transform
                  ${preferences.email_enabled ? 'translate-x-6' : 'translate-x-1'}
                `}
              />
            </button>
          </div>

          {/* Delivery Time */}
          <Input
            type="time"
            label="Delivery Time"
            value={preferences.delivery_time || '07:00'}
            onChange={(e) => setPreferences({ ...preferences, delivery_time: e.target.value })}
            helperText="What time should we send your daily reflection?"
          />

          {/* Timezone */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Timezone</label>
            <select
              value={preferences.timezone || 'America/New_York'}
              onChange={(e) => setPreferences({ ...preferences, timezone: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="America/New_York">Eastern Time (ET)</option>
              <option value="America/Chicago">Central Time (CT)</option>
              <option value="America/Denver">Mountain Time (MT)</option>
              <option value="America/Los_Angeles">Pacific Time (PT)</option>
              <option value="America/Anchorage">Alaska Time (AKT)</option>
              <option value="Pacific/Honolulu">Hawaii Time (HT)</option>
              <option value="Europe/London">London (GMT)</option>
              <option value="Europe/Paris">Paris (CET)</option>
              <option value="Asia/Tokyo">Tokyo (JST)</option>
              <option value="Australia/Sydney">Sydney (AEDT)</option>
            </select>
          </div>
        </div>

        <div className="mt-6 flex items-center justify-between">
          {saveSuccess && (
            <span className="text-sm text-green-600 font-semibold">
              ✓ Settings saved successfully!
            </span>
          )}
          <div className="ml-auto">
            <Button onClick={handleSave} isLoading={saving}>
              Save Preferences
            </Button>
          </div>
        </div>
      </Card>

      {/* Danger Zone */}
      <Card className="border-2 border-red-200">
        <h2 className="text-xl font-semibold text-red-600 mb-4">Danger Zone</h2>

        {!showDeleteConfirm ? (
          <div>
            <p className="text-gray-600 mb-4">
              Permanently delete your account and all associated data. This action cannot be undone.
            </p>
            <Button variant="danger" onClick={() => setShowDeleteConfirm(true)}>
              Delete Account
            </Button>
          </div>
        ) : (
          <div>
            <p className="text-red-600 font-semibold mb-4">
              Are you sure? This will permanently delete your account, all journal entries, and preferences.
              This action cannot be undone.
            </p>
            <div className="flex gap-3">
              <Button variant="danger" onClick={handleDeleteAccount} isLoading={deleting}>
                Yes, Delete My Account
              </Button>
              <Button variant="secondary" onClick={() => setShowDeleteConfirm(false)}>
                Cancel
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* Sign Out */}
      <div className="mt-8 text-center">
        <button
          onClick={() => logout().then(() => navigate('/login'))}
          className="text-gray-600 hover:text-gray-800 font-semibold"
        >
          Sign Out
        </button>
      </div>
    </div>
  );
}
