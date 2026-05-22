'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/app/AuthProvider';
import { User, Key, Database, Server, Save } from 'lucide-react';
import { authAPI } from '@/lib/api';

export default function SettingsPage() {
  const { user, setUser } = useAuth();
  const [saving, setSaving] = useState(false);
  const [settings, setSettings] = useState({
    apiEndpoint: 'http://localhost:8000/api/v1',
    ocrEnabled: true,
    maxUploadSize: 50,
    autoProcess: true,
  });

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const storedEndpoint = localStorage.getItem('api_endpoint') || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
      setSettings((prev) => ({
        ...prev,
        apiEndpoint: storedEndpoint,
      }));
    }
  }, []);

  useEffect(() => {
    if (user) {
      setSettings((prev) => ({
        ...prev,
        ocrEnabled: user.ocrEnabled,
        maxUploadSize: user.maxUploadSize,
        autoProcess: user.autoProcess,
      }));
    }
  }, [user]);

  const handleSave = async () => {
    setSaving(true);
    try {
      if (typeof window !== 'undefined') {
        localStorage.setItem('api_endpoint', settings.apiEndpoint);
      }
      
      const res = await authAPI.updateSettings({
        ocr_enabled: settings.ocrEnabled,
        max_upload_size: settings.maxUploadSize,
        auto_process: settings.autoProcess,
      });

      const updatedUser = res.data;
      
      if (user) {
        setUser({
          ...user,
          fullName: updatedUser.full_name || user.fullName,
          ocrEnabled: updatedUser.ocr_enabled,
          maxUploadSize: updatedUser.max_upload_size,
          autoProcess: updatedUser.auto_process,
        });
      }
      alert('Settings saved successfully!');
    } catch (error) {
      console.error('Failed to save settings:', error);
      alert('Failed to save settings. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <div className="mb-8">
        <h1
          className="text-4xl font-bold"
          style={{ color: 'var(--aluminum)', fontFamily: 'Manrope, sans-serif' }}
        >
          Settings
        </h1>
        <p
          className="text-sm mt-2"
          style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}
        >
          Manage your account and preferences
        </p>
      </div>

      <div className="space-y-6">
        {/* User Profile */}
        <div
          className="rounded-lg p-6"
          style={{
            background: 'rgba(26, 26, 46, 0.5)',
            border: '1px solid rgba(74, 74, 90, 0.4)',
          }}
        >
          <div className="flex items-center gap-3 mb-6">
            <User size={24} style={{ color: 'var(--orange)' }} />
            <h2
              className="text-xl font-bold"
              style={{ color: 'var(--aluminum)', fontFamily: 'Manrope, sans-serif' }}
            >
              Profile
            </h2>
          </div>
          <div className="space-y-4">
            <div>
              <label
                className="block text-sm mb-2"
                style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}
              >
                Email
              </label>
              <input
                type="email"
                value={user?.email || ''}
                disabled
                className="input-field w-full"
                style={{ opacity: 0.6 }}
              />
            </div>
            <div>
              <label
                className="block text-sm mb-2"
                style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}
              >
                Full Name
              </label>
              <input
                type="text"
                value={user?.fullName || ''}
                disabled
                className="input-field w-full"
                style={{ opacity: 0.6 }}
              />
            </div>
          </div>
        </div>

        {/* API Configuration */}
        <div
          className="rounded-lg p-6"
          style={{
            background: 'rgba(26, 26, 46, 0.5)',
            border: '1px solid rgba(74, 74, 90, 0.4)',
          }}
        >
          <div className="flex items-center gap-3 mb-6">
            <Server size={24} style={{ color: 'var(--orange)' }} />
            <h2
              className="text-xl font-bold"
              style={{ color: 'var(--aluminum)', fontFamily: 'Manrope, sans-serif' }}
            >
              API Configuration
            </h2>
          </div>
          <div className="space-y-4">
            <div>
              <label
                className="block text-sm mb-2"
                style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}
              >
                API Endpoint
              </label>
              <input
                type="text"
                value={settings.apiEndpoint}
                onChange={(e) => setSettings({ ...settings, apiEndpoint: e.target.value })}
                className="input-field w-full"
              />
            </div>
          </div>
        </div>

        {/* OCR Settings */}
        <div
          className="rounded-lg p-6"
          style={{
            background: 'rgba(26, 26, 46, 0.5)',
            border: '1px solid rgba(74, 74, 90, 0.4)',
          }}
        >
          <div className="flex items-center gap-3 mb-6">
            <Key size={24} style={{ color: 'var(--orange)' }} />
            <h2
              className="text-xl font-bold"
              style={{ color: 'var(--aluminum)', fontFamily: 'Manrope, sans-serif' }}
            >
              OCR Settings
            </h2>
          </div>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p
                  className="text-sm font-semibold"
                  style={{ color: 'var(--aluminum)', fontFamily: 'Manrope, sans-serif' }}
                >
                  Enable OCR by default
                </p>
                <p
                  className="text-xs"
                  style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}
                >
                  Automatically use OCR for scanned PDFs
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.ocrEnabled}
                  onChange={(e) => setSettings({ ...settings, ocrEnabled: e.target.checked })}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-orange" />
              </label>
            </div>
          </div>
        </div>

        {/* Upload Settings */}
        <div
          className="rounded-lg p-6"
          style={{
            background: 'rgba(26, 26, 46, 0.5)',
            border: '1px solid rgba(74, 74, 90, 0.4)',
          }}
        >
          <div className="flex items-center gap-3 mb-6">
            <Database size={24} style={{ color: 'var(--orange)' }} />
            <h2
              className="text-xl font-bold"
              style={{ color: 'var(--aluminum)', fontFamily: 'Manrope, sans-serif' }}
            >
              Upload Settings
            </h2>
          </div>
          <div className="space-y-4">
            <div>
              <label
                className="block text-sm mb-2"
                style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}
              >
                Max Upload Size (MB)
              </label>
              <input
                type="number"
                value={settings.maxUploadSize}
                onChange={(e) =>
                  setSettings({ ...settings, maxUploadSize: parseInt(e.target.value) })
                }
                className="input-field w-full"
                min="1"
                max="100"
              />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p
                  className="text-sm font-semibold"
                  style={{ color: 'var(--aluminum)', fontFamily: 'Manrope, sans-serif' }}
                >
                  Auto-process uploads
                </p>
                <p
                  className="text-xs"
                  style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}
                >
                  Automatically process PDFs after upload
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.autoProcess}
                  onChange={(e) => setSettings({ ...settings, autoProcess: e.target.checked })}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-orange" />
              </label>
            </div>
          </div>
        </div>

        {/* Save Button */}
        <div className="flex justify-end gap-4">
          <button
            onClick={handleSave}
            disabled={saving}
            className="btn-primary py-3 px-6 flex items-center gap-2 disabled:opacity-50"
          >
            <Save size={18} />
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </div>
    </div>
  );
}
