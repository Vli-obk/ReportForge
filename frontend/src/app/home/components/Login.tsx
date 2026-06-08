'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import FormInput from '@/components/FormInput';
import FormButton from '@/components/FormButton';
import FormCheckbox from '@/components/FormCheckbox';
import { useAuth } from '@/app/AuthProvider';
import { authAPI } from '@/lib/api';

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
      newErrors.email = 'Email valide requis';
    }
    if (!password || password.length < 6) {
      newErrors.password = 'Mot de passe requis (min 6 caractères)';
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
        ocrEnabled: userData.ocr_enabled ?? true,
        maxUploadSize: userData.max_upload_size ?? 50,
        autoProcess: userData.auto_process ?? true,
      });

      router.push('/home/dashboard');
    } catch (error: any) {
      console.error('Login error:', error);
      const detail = error.response?.data?.detail || 'Connexion échouée. Veuillez vérifier vos identifiants.';
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
              Bon Retour
            </h1>
            <p
              className="text-sm"
              style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}
            >
              Connectez-vous à votre compte ReportForge
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <FormInput
              label="Email"
              type="email"
              placeholder="vous@exemple.com"
              value={email}
              onChange={setEmail}
              error={errors.email}
              disabled={loading}
            />

            <FormInput
              label="Mot de passe"
              type="password"
              placeholder="Entrez votre mot de passe"
              value={password}
              onChange={setPassword}
              error={errors.password}
              disabled={loading}
            />

            <div className="flex items-center justify-between">
              <FormCheckbox
                label="Se souvenir de moi"
                checked={rememberMe}
                onChange={setRememberMe}
                disabled={loading}
              />
              <Link
                href="/home/forgot-password"
                className="text-xs transition-colors hover:text-orange"
                style={{
                  color: 'var(--aluminum-dim)',
                  fontFamily: 'JetBrains Mono, monospace',
                }}
              >
                Mot de passe oublié ?
              </Link>
            </div>

            <FormButton type="submit" variant="primary" loading={loading} fullWidth>
              Se Connecter
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
              Pas de compte ?{' '}
              <Link
                href="/home/register"
                className="text-orange hover:text-orange-dim transition-colors font-semibold"
              >
                S'inscrire
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
