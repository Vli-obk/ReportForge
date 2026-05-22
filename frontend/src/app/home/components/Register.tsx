'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import FormInput from '@/components/FormInput';
import FormButton from '@/components/FormButton';
import FormCheckbox from '@/components/FormCheckbox';
import { useAuth } from '@/app/AuthProvider';
import { authAPI } from '@/lib/api';

export default function RegisterPage() {
  const router = useRouter();
  const { setToken, setUser } = useAuth();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [agreeTOS, setAgreeTOS] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<{
    fullName?: string;
    email?: string;
    password?: string;
    confirmPassword?: string;
    tos?: string;
  }>({});

  const validateForm = (): boolean => {
    const newErrors: any = {};

    if (!fullName || fullName.trim().length < 2) {
      newErrors.fullName = 'Full name required (min 2 chars)';
    }
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      newErrors.email = 'Valid email required';
    }
    if (!password || password.length < 6) {
      newErrors.password = 'Password required (min 6 chars)';
    }
    if (password !== confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }
    if (!agreeTOS) {
      newErrors.tos = 'You must agree to the terms';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) return;

    setLoading(true);
    setErrors({});

    try {
      // 1. Call Register
      await authAPI.register({
        email,
        full_name: fullName,
        password,
      });

      // 2. Automatically log in after registration
      const loginRes = await authAPI.login(email, password);
      const token = loginRes.data.access_token;

      // Store token
      setToken(token);

      // Fetch user profile
      const userRes = await authAPI.getMe();
      const userData = userRes.data;

      // Store user info
      setUser({
        id: userData.id.toString(),
        email: userData.email,
        fullName: userData.full_name || userData.email.split('@')[0],
      });

      router.push('/home/dashboard');
    } catch (error: any) {
      console.error('Registration error:', error);
      const detail =
        error.response?.data?.detail || 'Registration failed. Email might already be taken.';
      setErrors({ email: detail });
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
              Create Account
            </h1>
            <p
              className="text-sm"
              style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}
            >
              Join PDF Analytics and get started
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <FormInput
              label="Full Name"
              type="text"
              placeholder="John Doe"
              value={fullName}
              onChange={setFullName}
              error={errors.fullName}
              disabled={loading}
            />

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

            <FormInput
              label="Confirm Password"
              type="password"
              placeholder="Confirm your password"
              value={confirmPassword}
              onChange={setConfirmPassword}
              error={errors.confirmPassword}
              disabled={loading}
            />

            <div>
              <FormCheckbox
                label="I agree to the Terms of Service"
                checked={agreeTOS}
                onChange={setAgreeTOS}
                disabled={loading}
              />
              {errors.tos && (
                <span
                  style={{
                    fontSize: '0.75rem',
                    color: '#FF6B6B',
                    fontFamily: 'JetBrains Mono, monospace',
                    marginTop: '4px',
                    display: 'block',
                  }}
                >
                  {errors.tos}
                </span>
              )}
            </div>

            <FormButton type="submit" variant="primary" loading={loading} fullWidth>
              Create Account
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
              Already have an account?{' '}
              <Link
                href="/home/login"
                className="text-orange hover:text-orange-dim transition-colors font-semibold"
              >
                Sign in
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
