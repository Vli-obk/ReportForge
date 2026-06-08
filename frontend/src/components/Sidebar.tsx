'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';

export default function Sidebar() {
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);

  const navItems = [
    { label: 'Tableau de bord', href: '/home/dashboard' },
    { label: 'Téléchargements', href: '/home/uploads' },
    { label: 'Jeux de données', href: '/home/datasets' },
    { label: 'Analytiques', href: '/home/analytics' },
    { label: 'Pipeline', href: '/home/pipeline' },
    { label: 'Paramètres', href: '/home/settings' },
  ];

  const isActive = (href: string) => {
    return pathname?.startsWith(href);
  };

  return (
    <>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed top-4 left-4 z-40 md:hidden p-2"
        style={{
          background: 'var(--graphite-light)',
          border: '1px solid var(--titanium)',
          borderRadius: '6px',
          color: 'var(--aluminum)',
        }}
      >
        ☰
      </button>

      <aside
        className={`fixed left-0 top-0 h-screen w-64 pt-20 md:pt-0 transition-transform duration-300 ${
          isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
        style={{
          background: 'var(--graphite-light)',
          borderRight: '1px solid rgba(74, 74, 90, 0.4)',
          zIndex: 30,
        }}
      >
        <nav className="flex flex-col gap-1 p-4">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setIsOpen(false)}
              className={`px-4 py-3 rounded-lg text-sm font-medium transition-all ${
                isActive(item.href) ? 'text-orange' : 'text-aluminum-dim hover:text-aluminum'
              }`}
              style={{
                background: isActive(item.href) ? 'rgba(255, 107, 43, 0.1)' : 'transparent',
                fontFamily: 'JetBrains Mono, monospace',
                borderLeft: isActive(item.href) ? '3px solid var(--orange)' : 'none',
              }}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </aside>

      {isOpen && (
        <div
          className="fixed inset-0 z-20 md:hidden"
          onClick={() => setIsOpen(false)}
          style={{ background: 'rgba(0, 0, 0, 0.5)' }}
        />
      )}
    </>
  );
}
