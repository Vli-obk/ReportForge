'use client';

import { useEffect, useRef, useState } from 'react';
import AppImage from '@/components/ui/AppImage';
import Link from 'next/link';
import { ScanText, Table2, Sparkles, Tags } from 'lucide-react';

const DOCUMENT_COUNT_TARGET = 1487;

function LiveCounter({ target }: { target: number }) {
  const [count, setCount] = useState(1212);
  const [ticking, setTicking] = useState(false);

  useEffect(() => {
    const timeout = setTimeout(() => {
      setTicking(true);
      const duration = 2200;
      const startTime = performance.now();
      const startVal = 1212;

      const tick = (now: number) => {
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = Math.floor(startVal + (target - startVal) * eased);
        setCount(current);
        if (progress < 1) requestAnimationFrame(tick);
        else setTicking(false);
      };
      requestAnimationFrame(tick);
    }, 800);
    return () => clearTimeout(timeout);
  }, [target]);

  return (
    <span className="counter-number" style={{ fontSize: 'inherit', fontWeight: 'inherit' }}>
      {count.toLocaleString()}
      {ticking && (
        <span
          className="pulse-dot inline-block w-1.5 h-1.5 rounded-full ml-1 align-middle"
          style={{ background: 'var(--orange)' }}
        />
      )}
    </span>
  );
}

const glassPanels = [
  {
    id: 1,
    label: 'Extraction OCR',
    sublabel: 'Tesseract · Actif',
    color: '#1A1A2E',
    style: { gridColumn: '1 / 3', gridRow: '1 / 3' },
    image: 'https://img.rocket.new/generatedImages/rocket_gen_img_1b66192b4-1767700391641.png',
    alt: 'OCR extraction interface with highlighted text fields',
    badge: 'TEXT',
    rating: '99%',
    icon: ScanText,
    href: '/home/uploads',
  },
  {
    id: 2,
    label: 'Analyse de Tableaux',
    sublabel: 'Pandas · Données',
    color: '#16162A',
    style: { gridColumn: '3 / 5', gridRow: '1 / 2' },
    image: 'https://img.rocket.new/generatedImages/rocket_gen_img_110bb8bb6-1765181843115.png',
    alt: 'Table parsing view with extracted rows and columns',
    badge: 'DATA',
    rating: '98%',
    icon: Table2,
    href: '/home/analytics',
  },
  {
    id: 3,
    label: 'Résumé IA',
    sublabel: 'LLM · Insights',
    color: '#12122A',
    style: { gridColumn: '5 / 7', gridRow: '1 / 3' },
    image: 'https://img.rocket.new/generatedImages/rocket_gen_img_120803e5a-1764651524476.png',
    alt: 'AI summary dashboard showing key insights and metrics',
    badge: 'AI',
    rating: '95%',
    icon: Sparkles,
    href: '/home/dashboard',
  },
  {
    id: 4,
    label: "Détection d'Entités",
    sublabel: 'NLP · Direct',
    color: '#1C1C30',
    style: { gridColumn: '3 / 5', gridRow: '2 / 3' },
    image: 'https://img.rocket.new/generatedImages/rocket_gen_img_1ab6dfbae-1765379263484.png',
    alt: 'Named entity recognition panel with tagged names and dates',
    badge: 'NLP',
    rating: '96%',
    icon: Tags,
    href: '/home/datasets',
  },
];

export default function HeroSection() {
  const containerRef = useRef<HTMLDivElement>(null);
  const panelsRef = useRef<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleMouseMove = (e: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      const dx = (e.clientX - cx) / rect.width;
      const dy = (e.clientY - cy) / rect.height;

      panelsRef.current.forEach((panel, i) => {
        if (!panel) return;
        const depth = [0.8, 0.5, 0.6, 0.4][i] ?? 0.5;
        const tx = dx * 14 * depth;
        const ty = dy * 10 * depth;
        panel.style.transform = `translate(${tx}px, ${ty}px)`;
      });
    };

    container.addEventListener('mousemove', handleMouseMove);
    return () => container.removeEventListener('mousemove', handleMouseMove);
  }, []);

  return (
    <section
      ref={containerRef}
      className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden pt-24 pb-16 px-6"
      style={{ background: 'var(--carbon)' }}
    >
      {/* Ambient glow */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            'radial-gradient(ellipse 70% 50% at 50% 30%, rgba(255,107,43,0.06) 0%, transparent 70%)',
        }}
      />

      <div className="relative z-10 max-w-7xl mx-auto w-full">
        <div className="flex justify-center mb-8">
          <span className="badge-orange">
            <span
              className="pulse-dot inline-block w-1.5 h-1.5 rounded-full mr-1.5 align-middle"
              style={{ background: 'var(--orange)' }}
            />
            ReportForge · Updated May 2026
          </span>
        </div>

        {/* Main headline */}
        <div className="text-center mb-12">
          <h1
            className="mono font-black leading-none tracking-tight mb-4"
            style={{ fontSize: 'clamp(2.5rem, 7vw, 6rem)', color: 'var(--aluminum)' }}
          >
            <LiveCounter target={DOCUMENT_COUNT_TARGET} /> PDFs traités.
          </h1>
          <h2
            className="mono font-bold leading-none tracking-tight"
            style={{ fontSize: 'clamp(1.8rem, 5vw, 4.2rem)', color: 'var(--aluminum-dim)' }}
          >
            Téléchargés. Extraits. Analysés.
          </h2>
          <p
            className="mt-6 max-w-xl mx-auto text-base leading-relaxed"
            style={{ color: 'var(--aluminum-dim)', fontFamily: 'Manrope, sans-serif' }}
          >
            Arrêtez de copier-coller manuellement. Chaque PDF, document scanné et facture —
            automatiquement extrait, structuré et analysé avec l'IA.
          </p>
        </div>

        {/* CTAs */}
        <div className="flex flex-col sm:flex-row gap-3 justify-center mb-16">
          <Link href="/home/login" className="btn-primary inline-block text-center cursor-pointer">
            Commencer Gratuitement — Télécharger des PDFs
          </Link>
          <Link
            href="/home/login"
            className="btn-secondary inline-block text-center cursor-pointer"
          >
            Débloquer Analytics Pro — 14 Jours
          </Link>
        </div>

        {/* Bento glass panels grid */}
        <div
          className="w-full relative"
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(6, 1fr)',
            gridTemplateRows: 'repeat(2, 180px)',
            gap: '10px',
            maxWidth: '960px',
            margin: '0 auto',
          }}
        >
          {glassPanels.map((panel, i) => {
            const Icon = panel.icon;
            return (
              <Link
                key={panel.id}
                href={panel.href}
                ref={(el) => {
                  panelsRef.current[i] = el as HTMLDivElement | null;
                }}
                className="glass-panel relative overflow-hidden cursor-pointer group"
                style={{
                  ...panel.style,
                  transition: 'transform 0.15s linear, border-color 0.3s ease',
                }}
              >
                {/* Background image */}
                <div className="absolute inset-0">
                  <AppImage
                    src={panel.image}
                    alt={panel.alt}
                    fill
                    className="object-cover opacity-30"
                    sizes="(max-width: 960px) 50vw, 33vw"
                  />
                </div>
                {/* Dark glass overlay */}
                <div
                  className="absolute inset-0"
                  style={{
                    background:
                      'linear-gradient(135deg, rgba(26,26,46,0.85) 0%, rgba(13,13,13,0.7) 100%)',
                  }}
                />

                {/* Content */}
                <div className="absolute inset-0 p-4 flex flex-col justify-between">
                  <div className="flex items-start justify-between">
                    <span className="badge-orange" style={{ fontSize: '0.6rem' }}>
                      {panel.badge}
                    </span>
                    <span className="mono text-xs font-bold" style={{ color: 'var(--orange)' }}>
                      ★ {panel.rating}
                    </span>
                  </div>
                  <div>
                    <Icon
                      size={panel.id === 1 ? 32 : 24}
                      style={{ color: 'var(--orange)', opacity: 0.85, marginBottom: '8px' }}
                    />
                    <p className="mono font-bold text-sm" style={{ color: 'var(--aluminum)' }}>
                      {panel.label}
                    </p>
                    <p className="mono text-xs" style={{ color: 'var(--aluminum-dim)' }}>
                      {panel.sublabel}
                    </p>
                  </div>
                </div>
                {/* Border glow on hover */}
                <div
                  className="absolute inset-0 rounded-[14px] pointer-events-none group-hover:border-orange-500/40 transition-all"
                  style={{ border: '1px solid rgba(255,107,43,0.1)' }}
                />
              </Link>
            );
          })}

          {/* Remaining 2 cells - stats */}
          <div
            className="glass-panel flex flex-col items-center justify-center p-4"
            style={{ gridColumn: '1 / 3', gridRow: '3 / 4', height: '120px' }}
          >
            <span className="mono font-black text-3xl" style={{ color: 'var(--orange)' }}>
              12k+
            </span>
            <span
              className="mono text-xs uppercase tracking-widest mt-1"
              style={{ color: 'var(--aluminum-dim)' }}
            >
              Utilisateurs
            </span>
          </div>
          <div
            className="glass-panel flex flex-col items-center justify-center p-4"
            style={{ gridColumn: '3 / 5', gridRow: '3 / 4', height: '120px' }}
          >
            <span className="mono font-black text-3xl" style={{ color: 'var(--orange)' }}>
              99%
            </span>
            <span
              className="mono text-xs uppercase tracking-widest mt-1"
              style={{ color: 'var(--aluminum-dim)' }}
            >
              Précision
            </span>
          </div>
          <div
            className="glass-panel flex flex-col items-center justify-center p-4"
            style={{ gridColumn: '5 / 7', gridRow: '3 / 4', height: '120px' }}
          >
            <span className="mono font-black text-3xl" style={{ color: 'var(--orange)' }}>
              0
            </span>
            <span
              className="mono text-xs uppercase tracking-widest mt-1"
              style={{ color: 'var(--aluminum-dim)' }}
            >
              Travail Manuel
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}
