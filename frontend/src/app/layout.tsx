import React from 'react';
import type { Metadata, Viewport } from 'next';
import '../styles/index.css';
import { AuthProvider } from '@/app/AuthProvider';
import { ApiQueryProvider } from '@/hooks/useApiQuery';

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
};

export const metadata: Metadata = {
  title: 'ReportForge - Document Intelligence Platform',
  description: 'Intelligent financial report processing platform',
  icons: {
    icon: [{ url: '/assets/images/app_logo.png', type: 'image/x-icon' }],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <ApiQueryProvider>
          <AuthProvider>{children}</AuthProvider>
        </ApiQueryProvider>
      </body>
    </html>
  );
}
