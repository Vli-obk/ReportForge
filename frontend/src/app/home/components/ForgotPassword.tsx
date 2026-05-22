'use client';

import { useState } from 'react';
import Link from 'next/link';
import FormInput from '@/components/FormInput';
import FormButton from '@/components/FormButton';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [errors, setErrors] = useState<{ email?: string }>({});

  const validateForm = (): boolean => {
    const newErrors: { email?: string } = {};

    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      newErrors.email = 'Valid email required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) return;

    setLoading(true);

    try {
      await new Promise((resolve) => setTimeout(resolve, 800));
      setSent(true);
    } catch (error) {
      setErrors({ email: 'Failed to send reset email. Please try again.' });
    } finally {
      setLoading(false);
    }
  };

  if (sent) {
    return (
      <div
        className="min-h-screen flex items-center justify-center px-4 py-12"
        style={{ background: 'var(--carbon)' }}
      >
        <div className="absolute inset-0 pointer-events-none" style={{ opacity: 0.3 }}>
          <div
            style={{
              position: 'absolute',
              top: '-40%',
              right: '-20%',
              width: '500px',
              height: '500px',
              background: 'radial-gradient(circle, rgba(255,107,43,0.1) 0%, transparent 70%)',
              borderRadius: '50%',
            }}
          />
        </div>

        <div className="w-full max-w-md relative z-10">
          <div
            className="rounded-2xl p-8 md:p-12 text-center"
            style={{
              background: 'rgba(26, 26, 46, 0.7)',
              backdropFilter: 'blur(16px)',
              WebkitBackdropFilter: 'blur(16px)',
              border: '1px solid rgba(74, 74, 90, 0.4)',
            }}
          >
            <h1
              className="text-3xl md:text-4xl font-bold mb-4"
              style={{ color: 'var(--aluminum)', fontFamily: 'Manrope, sans-serif' }}
            >
              Check Your Email
            </h1>
            <p
              className="text-sm mb-6"
              style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}
            >
              We've sent a password reset link to <strong>{email}</strong>
            </p>

            <Link href="/home/login" className="btn-primary inline-block">
              Back to Login
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center px-4 py-12"
      style={{ background: 'var(--carbon)' }}
    >
      <div className="absolute inset-0 pointer-events-none" style={{ opacity: 0.3 }}>
        <div
          style={{
            position: 'absolute',
            top: '-40%',
            right: '-20%',
            width: '500px',
            height: '500px',
            background: 'radial-gradient(circle, rgba(255,107,43,0.1) 0%, transparent 70%)',
            borderRadius: '50%',
          }}
        />
      </div>

      <div className="w-full max-w-md relative z-10">
        <div
          className="rounded-2xl p-8 md:p-12"
          style={{
            background: 'rgba(26, 26, 46, 0.7)',
            backdropFilter: 'blur(16px)',
            WebkitBackdropFilter: 'blur(16px)',
            border: '1px solid rgba(74, 74, 90, 0.4)',
          }}
        >
          <div className="mb-8">
            <h1
              className="text-3xl md:text-4xl font-bold mb-2"
              style={{ color: 'var(--aluminum)', fontFamily: 'Manrope, sans-serif' }}
            >
              Reset Password
            </h1>
            <p
              className="text-sm"
              style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}
            >
              Enter your email to receive a reset link
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <FormInput
              label="Email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={setEmail}
              error={errors.email}
              disabled={loading}
            />

            <FormButton type="submit" variant="primary" loading={loading} fullWidth>
              Send Reset Link
            </FormButton>
          </form>

          <div
            className="mt-6 pt-6 border-t text-center"
            style={{ borderColor: 'rgba(74, 74, 90, 0.4)' }}
          >
            <Link
              href="/home/login"
              className="text-xs transition-colors hover:text-orange"
              style={{
                color: 'var(--aluminum-dim)',
                fontFamily: 'JetBrains Mono, monospace',
              }}
            >
              ← Back to login
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
