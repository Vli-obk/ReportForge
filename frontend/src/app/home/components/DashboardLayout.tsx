'use client';

import { useAuth } from '@/app/AuthProvider';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import Sidebar from '@/components/Sidebar';
import TopNav from '@/components/TopNav';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/home/login');
    }
  }, [isAuthenticated, router]);

  if (!isAuthenticated) {
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
          background: 'var(--carbon)',
        }}
      >
        <div style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}>
          Redirecting to login...
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--carbon)' }}>
      <Sidebar />
      <div className="flex-1 flex flex-col md:ml-64">
        <TopNav />
        <main
          className="flex-1 pt-20 md:pt-16 px-4 md:px-8 py-6"
          style={{
            background: 'var(--carbon)',
          }}
        >
          <div className="max-w-7xl mx-auto">{children}</div>
        </main>
      </div>
    </div>
  );
}
