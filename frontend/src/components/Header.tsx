'use client';

import AppLogo from '@/components/ui/AppLogo';
import Link from 'next/link';

export default function Header() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 px-6 py-4">
      <div
        className="max-w-7xl mx-auto flex items-center justify-between"
        style={{
          background: 'rgba(13, 13, 13, 0.85)',
          backdropFilter: 'blur(16px)',
          WebkitBackdropFilter: 'blur(16px)',
          border: '1px solid rgba(74, 74, 90, 0.4)',
          borderRadius: '10px',
          padding: '12px 24px',
        }}
      >
        <AppLogo
          text="PDF Analytics"
          iconName="DocumentChartBarIcon"
          size={28}
          className="text-aluminum font-mono font-bold tracking-tight"
        />

        <div
          className="hidden md:flex items-center gap-8 text-sm font-medium"
          style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}
        >
          <Link
            href="#categories"
            className="hover:text-aluminum transition-colors text-xs uppercase tracking-widest"
          >
            Categories
          </Link>
          <Link
            href="#leaderboard"
            className="hover:text-aluminum transition-colors text-xs uppercase tracking-widest"
          >
            Top Models
          </Link>
          <Link
            href="#compatibility"
            className="hover:text-aluminum transition-colors text-xs uppercase tracking-widest"
          >
            Pipelines
          </Link>
          <Link
            href="#pro"
            className="hover:text-aluminum transition-colors text-xs uppercase tracking-widest"
          >
            Pro
          </Link>
        </div>

        <Link
          href="/home/login"
          className="btn-primary text-xs py-2.5 px-5 inline-block text-center"
        >
          Start Free
        </Link>
      </div>
    </nav>
  );
}
