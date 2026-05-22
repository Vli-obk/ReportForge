'use client';

import Link from 'next/link';
import AppLogo from '@/components/ui/AppLogo';
import { useAuth } from '@/app/AuthProvider';
import { useState } from 'react';

export default function TopNav() {
  const { user, logout } = useAuth();
  const [showUserMenu, setShowUserMenu] = useState(false);

  return (
    <nav
      className="fixed top-0 left-0 right-0 h-16 z-40 md:left-64 border-b"
      style={{
        background: 'var(--carbon)',
        borderColor: 'rgba(74, 74, 90, 0.4)',
      }}
    >
      <div className="h-full px-6 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <AppLogo
            text="PDF Analytics"
            iconName="CubeTransparentIcon"
            size={24}
            className="hidden md:flex text-aluminum font-mono font-bold"
          />
          <span
            className="text-sm"
            style={{
              color: 'var(--aluminum-dim)',
              fontFamily: 'JetBrains Mono, monospace',
            }}
          >
            Dashboard
          </span>
        </div>

        <div className="relative">
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg transition-all"
            style={{
              background: 'rgba(74, 74, 90, 0.2)',
              border: '1px solid rgba(74, 74, 90, 0.4)',
              color: 'var(--aluminum)',
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '0.875rem',
            }}
          >
            <span className="hidden sm:inline">{user?.email}</span>
            <span>▼</span>
          </button>

          {showUserMenu && (
            <div
              className="absolute right-0 top-full mt-2 w-48 rounded-lg shadow-lg py-1"
              style={{
                background: 'var(--graphite-light)',
                border: '1px solid rgba(74, 74, 90, 0.4)',
                zIndex: 50,
              }}
            >
              <Link
                href="/home/settings"
                className="block px-4 py-2 text-sm transition-colors hover:text-orange"
                style={{
                  color: 'var(--aluminum)',
                  fontFamily: 'JetBrains Mono, monospace',
                }}
              >
                Profile
              </Link>
              <Link
                href="/home/settings"
                className="block px-4 py-2 text-sm transition-colors hover:text-orange"
                style={{
                  color: 'var(--aluminum)',
                  fontFamily: 'JetBrains Mono, monospace',
                }}
              >
                Settings
              </Link>
              <button
                onClick={() => {
                  logout();
                  setShowUserMenu(false);
                  window.location.href = '/home/login';
                }}
                className="w-full text-left px-4 py-2 text-sm transition-colors hover:text-orange"
                style={{
                  color: 'var(--aluminum)',
                  fontFamily: 'JetBrains Mono, monospace',
                  borderTop: '1px solid rgba(74, 74, 90, 0.4)',
                }}
              >
                Logout
              </button>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}
