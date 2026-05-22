'use client';

import { useEffect, useState } from 'react';

export default function StickyBar() {
  const [visible, setVisible] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      if (dismissed) return;
      const scrolled = window.scrollY;
      const viewportH = window.innerHeight;
      setVisible(scrolled > viewportH * 1.6);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, [dismissed]);

  if (dismissed) return null;

  return (
    <div className={`sticky-bar ${visible ? 'visible' : ''}`}>
      <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <span
            className="pulse-dot inline-block w-2 h-2 rounded-full shrink-0"
            style={{ background: 'var(--orange)' }}
          />
          <p className="mono text-xs truncate" style={{ color: 'var(--aluminum-dim)' }}>
            <span style={{ color: 'var(--aluminum)' }}>1487 pipelines active.</span> Accuracy reports,
            model recommendations, and extraction alerts — Pro tier.
          </p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <button className="btn-primary py-2 px-4 text-xs">
            Start Free — Unlock Pro Analytics
          </button>
          <button
            onClick={() => setDismissed(true)}
            className="mono text-xs p-1 hover:text-aluminum transition-colors"
            style={{ color: 'var(--titanium-light)' }}
            aria-label="Dismiss"
          >
            ✕
          </button>
        </div>
      </div>
    </div>
  );
}
