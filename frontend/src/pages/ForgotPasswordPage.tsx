/**
 * Forgot Password Page
 *
 * Handles password reset request and confirmation
 */

import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/Button';
import { Input } from '../components/Input';
import { Card } from '../components/Card';
import { isValidEmail, isValidPassword, isValidVerificationCode } from '../utils/validation';

type Step = 'request' | 'reset';

export function ForgotPasswordPage() {
  const navigate = useNavigate();
  const { requestPasswordReset, confirmPasswordReset } = useAuth();

  const [step, setStep] = useState<Step>('request');
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [generalError, setGeneralError] = useState('');

  const validateRequest = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!email) {
      newErrors.email = 'Email is required';
    } else if (!isValidEmail(email)) {
      newErrors.email = 'Please enter a valid email';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const validateReset = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!code) {
      newErrors.code = 'Verification code is required';
    } else if (!isValidVerificationCode(code)) {
      newErrors.code = 'Please enter a valid 6-digit code';
    }

    if (!newPassword) {
      newErrors.newPassword = 'Password is required';
    } else {
      const passwordValidation = isValidPassword(newPassword);
      if (!passwordValidation.valid) {
        newErrors.newPassword = passwordValidation.errors[0];
      }
    }

    if (!confirmPassword) {
      newErrors.confirmPassword = 'Please confirm your password';
    } else if (newPassword !== confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleRequestSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setGeneralError('');

    if (!validateRequest()) {
      return;
    }

    try {
      setIsLoading(true);
      await requestPasswordReset(email);
      setStep('reset');
    } catch (error) {
      console.error('Password reset request error:', error);
      setGeneralError(
        error instanceof Error ? error.message : 'Failed to send reset code. Please try again.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleResetSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setGeneralError('');

    if (!validateReset()) {
      return;
    }

    try {
      setIsLoading(true);
      await confirmPasswordReset(email, code, newPassword);
      navigate('/login', {
        state: { message: 'Password reset successfully! Please sign in with your new password.' }
      });
    } catch (error) {
      console.error('Password reset error:', error);
      setGeneralError(
        error instanceof Error ? error.message : 'Failed to reset password. Please try again.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  if (step === 'request') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="max-w-md w-full">
          <div className="text-center mb-8">
            <h1 className="text-4xl font-serif text-stoic-800 mb-2">Reset Password</h1>
            <p className="text-gray-600">Enter your email to receive a reset code</p>
          </div>

          <Card>
            <form onSubmit={handleRequestSubmit} className="space-y-4">
              <Input
                type="email"
                label="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                error={errors.email}
                placeholder="you@example.com"
                autoComplete="email"
                autoFocus
              />

              {generalError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-sm text-red-600">{generalError}</p>
                </div>
              )}

              <Button type="submit" fullWidth isLoading={isLoading}>
                Send Reset Code
              </Button>
            </form>

            <div className="mt-6 text-center">
              <Link
                to="/login"
                className="text-sm text-gray-600 hover:text-gray-800"
              >
                Back to Sign In
              </Link>
            </div>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="max-w-md w-full">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-serif text-stoic-800 mb-2">Reset Password</h1>
          <p className="text-gray-600">
            We sent a reset code to <strong>{email}</strong>
          </p>
        </div>

        <Card>
          <form onSubmit={handleResetSubmit} className="space-y-4">
            <Input
              type="text"
              label="Verification Code"
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              error={errors.code}
              placeholder="Enter 6-digit code"
              maxLength={6}
              autoFocus
            />

            <Input
              type="password"
              label="New Password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              error={errors.newPassword}
              placeholder="Create a strong password"
              autoComplete="new-password"
              helperText="Min 12 characters, with uppercase, lowercase, digit, and special character"
            />

            <Input
              type="password"
              label="Confirm Password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              error={errors.confirmPassword}
              placeholder="Re-enter your password"
              autoComplete="new-password"
            />

            {generalError && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-600">{generalError}</p>
              </div>
            )}

            <Button type="submit" fullWidth isLoading={isLoading}>
              Reset Password
            </Button>
          </form>

          <div className="mt-6 text-center">
            <button
              onClick={() => setStep('request')}
              className="text-sm text-gray-600 hover:text-gray-800"
            >
              Didn't receive the code? Resend
            </button>
          </div>
        </Card>
      </div>
    </div>
  );
}
