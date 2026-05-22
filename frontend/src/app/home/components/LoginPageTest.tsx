'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import FormInput from '@/components/FormInput';
import FormButton from '@/components/FormButton';
import FormCheckbox from '@/components/FormCheckbox';
import { useAuth } from '@/app/AuthProvider';

export default function LoginPage() {
  const router = useRouter();
  const { setToken, setUser } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});

  const validateForm = (): boolean => {
    const newErrors: { email?: string; password?: string } = {};

    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      newErrors.email = 'Valid email required';
    }
    if (!password || password.length < 6) {
      newErrors.password = 'Password required (min 6 chars)';
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

      const token = 'mock_token_' + Date.now();
      const user = {
        id: '1',
        email: email,
        fullName: email.split('@')[0],
      };

      setToken(token);
      setUser(user);

      router.push('/dashboard');
    } catch (error) {
      setErrors({ email: 'Login failed. Please try again.' });
    } finally {
      setLoading(false);
    }
  };

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
              Welcome Back
            </h1>
            <p
              className="text-sm"
              style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}
            >
              Sign in to your PDF Analytics account
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

            <FormInput
              label="Password"
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={setPassword}
              error={errors.password}
              disabled={loading}
            />

            <div className="flex items-center justify-between">
              <FormCheckbox
                label="Remember me"
                checked={rememberMe}
                onChange={setRememberMe}
                disabled={loading}
              />
              <Link
                href="/forgot-password"
                className="text-xs transition-colors hover:text-orange"
                style={{
                  color: 'var(--aluminum-dim)',
                  fontFamily: 'JetBrains Mono, monospace',
                }}
              >
                Forgot password?
              </Link>
            </div>

            <FormButton type="submit" variant="primary" loading={loading} fullWidth>
              Sign In
            </FormButton>
          </form>

          <div
            className="mt-6 pt-6 border-t text-center"
            style={{ borderColor: 'rgba(74, 74, 90, 0.4)' }}
          >
            <p
              className="text-xs"
              style={{
                color: 'var(--aluminum-dim)',
                fontFamily: 'JetBrains Mono, monospace',
              }}
            >
              Don't have an account?{' '}
              <Link
                href="/register"
                className="text-orange hover:text-orange-dim transition-colors font-semibold"
              >
                Sign up
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
