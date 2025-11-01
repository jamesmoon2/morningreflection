/**
 * Email Verification Page
 *
 * Handles email verification with 6-digit code
 */

import React, { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/Button';
import { Input } from '../components/Input';
import { Card } from '../components/Card';
import { isValidVerificationCode } from '../utils/validation';

export function VerifyEmailPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { confirmSignup } = useAuth();

  const emailFromState = (location.state as { email?: string })?.email || '';

  const [email, setEmail] = useState(emailFromState);
  const [code, setCode] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [generalError, setGeneralError] = useState('');

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!email) {
      newErrors.email = 'Email is required';
    }

    if (!code) {
      newErrors.code = 'Verification code is required';
    } else if (!isValidVerificationCode(code)) {
      newErrors.code = 'Please enter a valid 6-digit code';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setGeneralError('');

    if (!validate()) {
      return;
    }

    try {
      setIsLoading(true);
      await confirmSignup(email, code);
      navigate('/login', {
        state: { message: 'Email verified successfully! Please sign in.' }
      });
    } catch (error) {
      console.error('Verification error:', error);
      setGeneralError(
        error instanceof Error ? error.message : 'Invalid verification code. Please try again.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="max-w-md w-full">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-serif text-stoic-800 mb-2">Verify Your Email</h1>
          <p className="text-gray-600">
            We sent a verification code to <strong>{email}</strong>
          </p>
        </div>

        <Card>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              type="email"
              label="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              error={errors.email}
              placeholder="you@example.com"
              autoComplete="email"
            />

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

            {generalError && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-600">{generalError}</p>
              </div>
            )}

            <Button type="submit" fullWidth isLoading={isLoading}>
              Verify Email
            </Button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-sm text-gray-600">
              Didn't receive the code?{' '}
              <button className="text-primary-600 hover:text-primary-700 font-semibold">
                Resend
              </button>
            </p>
            <Link
              to="/login"
              className="block mt-2 text-sm text-gray-600 hover:text-gray-800"
            >
              Back to Sign In
            </Link>
          </div>
        </Card>
      </div>
    </div>
  );
}
