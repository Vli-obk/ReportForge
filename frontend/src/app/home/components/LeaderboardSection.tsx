'use client';

import { useEffect, useRef } from 'react';
import AppImage from '@/components/ui/AppImage';

const topPipelines = [
  {
    rank: 1,
    name: 'Invoice OCR Model',
    category: 'Factures / Reçus',
    processed: '1.2M',
    rating: 4.9,
    change: '+210k',
    positive: true,
    avatar: 'https://img.rocket.new/generatedImages/rocket_gen_img_1143b1d2e-1768304031741.png',
    avatarAlt: 'Invoice processing dashboard',
    tags: ['OCR', 'Finance'],
    verified: true,
  },
  {
    rank: 2,
    name: 'Table Extractor v2',
    category: 'Finances',
    processed: '842k',
    rating: 4.9,
    change: '+184k',
    positive: true,
    avatar: 'https://img.rocket.new/generatedImages/rocket_gen_img_15f7dcde7-1768810396285.png',
    avatarAlt: 'Table extraction interface',
    tags: ['Tables', 'Data'],
    verified: true,
  },
  {
    rank: 3,
    name: 'Legal Clause Parser',
    category: 'Contrats',
    processed: '654k',
    rating: 4.8,
    change: '+134k',
    positive: true,
    avatar: 'https://img.rocket.new/generatedImages/rocket_gen_img_1fa46441c-1770983315125.png',
    avatarAlt: 'Legal contract parsing preview',
    tags: ['NLP', 'Legal'],
    verified: true,
  },
  {
    rank: 4,
    name: 'HIPAA PII Redactor',
    category: 'Santé',
    processed: '521k',
    rating: 4.7,
    change: '+92k',
    positive: true,
    avatar: 'https://img.rocket.new/generatedImages/rocket_gen_img_16a0dc319-1766561206892.png',
    avatarAlt: 'Healthcare PII redaction screen',
    tags: ['HIPAA'],
    verified: true,
  },
  {
    rank: 5,
    name: 'Waybill Scanner',
    category: 'Logistique',
    processed: '419k',
    rating: 4.6,
    change: '+124k',
    positive: true,
    avatar: 'https://img.rocket.new/generatedImages/rocket_gen_img_168ca8a5f-1769253804882.png',
    avatarAlt: 'Waybill tracking and extraction',
    tags: ['Logistics'],
    verified: false,
  },
];

const risingModels = [
  {
    name: 'Gemini Vision Pro',
    growth: '+184%',
    week: 'cette semaine',
    bars: [30, 45, 38, 62, 55, 78, 84],
  },
  { name: 'GPT-4o Parser', growth: '+161%', week: 'cette semaine', bars: [20, 35, 42, 38, 55, 60, 61] },
  { name: 'Claude Sonnet', growth: '+147%', week: 'cette semaine', bars: [40, 38, 44, 41, 48, 45, 47] },
  {
    name: 'Llama 3 Instruct',
    growth: '+139%',
    week: 'cette semaine',
    bars: [25, 28, 30, 34, 32, 37, 39],
  },
];

function MiniChart({ bars }: { bars: number[] }) {
  const max = Math.max(...bars);
  return (
    <div className="flex items-end gap-0.5" style={{ height: '28px' }}>
      {bars.map((bar, i) => (
        <div
          key={i}
          className="rounded-sm flex-1"
          style={{
            height: `${(bar / max) * 100}%`,
            background: i === bars.length - 1 ? 'var(--orange)' : 'rgba(255,107,43,0.3)',
            minWidth: '4px',
            transition: `height 0.6s cubic-bezier(0.25,0.46,0.45,0.94) ${i * 60}ms`,
          }}
        />
      ))}
    </div>
  );
}

export default function LeaderboardSection() {
  const sectionRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.querySelectorAll('.reveal').forEach((el, i) => {
              setTimeout(() => el.classList.add('visible'), i * 80);
            });
          }
        });
      },
      { threshold: 0.1 }
    );
    if (sectionRef.current) observer.observe(sectionRef.current);
    return () => observer.disconnect();
  }, []);

  return (
    <section
      id="leaderboard"
      ref={sectionRef}
      className="py-20 px-6"
      style={{ background: '#0A0A18' }}
    >
      <div className="max-w-7xl mx-auto">
        <div className="mb-10">
          <span
            className="mono text-xs uppercase tracking-widest"
            style={{ color: 'var(--orange)' }}
          >
            // 02 — Rapport de l'Écosystème
          </span>
          <h2
            className="mono font-black text-3xl md:text-4xl mt-2"
            style={{ color: 'var(--aluminum)' }}
          >
            Les Extractions du Mois.
          </h2>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
          {/* Wide leaderboard */}
          <div
            className="bento-card reveal lg:col-span-2 overflow-hidden"
            style={{ background: 'var(--graphite)' }}
          >
            <div className="p-5 border-b" style={{ borderColor: 'rgba(74,74,90,0.4)' }}>
              <div className="flex items-center justify-between">
                <span className="mono font-bold text-sm" style={{ color: 'var(--aluminum)' }}>
                  Les Plus Traités — Mai 2026
                </span>
                <span className="badge-orange">LIVE</span>
              </div>
            </div>
            <div className="divide-y" style={{ borderColor: 'rgba(74,74,90,0.3)' }}>
              {topPipelines.map((pipeline, i) => (
                <div
                  key={pipeline.name}
                  className="reveal flex items-center gap-4 px-5 py-4 hover:bg-white/[0.02] transition-colors cursor-pointer group"
                  style={{ transitionDelay: `${i * 60}ms` }}
                >
                  <span
                    className="mono font-black text-lg w-6 text-center shrink-0"
                    style={{ color: i === 0 ? 'var(--orange)' : 'var(--titanium)' }}
                  >
                    {pipeline.rank}
                  </span>
                  <div
                    className="w-10 h-10 rounded-lg overflow-hidden shrink-0 border"
                    style={{ borderColor: 'rgba(74,74,90,0.4)' }}
                  >
                    <AppImage
                      src={pipeline.avatar}
                      alt={pipeline.avatarAlt}
                      width={40}
                      height={40}
                      className="object-cover w-full h-full"
                    />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span
                        className="mono font-bold text-sm truncate"
                        style={{ color: 'var(--aluminum)' }}
                      >
                        {pipeline.name}
                      </span>
                      {pipeline.verified && (
                        <span
                          className="shrink-0 w-4 h-4 rounded-full flex items-center justify-center text-xs"
                          style={{ background: 'var(--orange)', color: '#0D0D0D' }}
                        >
                          ✓
                        </span>
                      )}
                    </div>
                    <p className="mono text-xs mt-0.5" style={{ color: 'var(--aluminum-dim)' }}>
                      {pipeline.category}
                    </p>
                  </div>
                  <div className="hidden md:flex items-center gap-2">
                    {pipeline.tags.map((tag) => (
                      <span key={tag} className="tag-pill">
                        {tag}
                      </span>
                    ))}
                  </div>
                  <div className="text-right shrink-0">
                    <p className="mono font-bold text-sm" style={{ color: 'var(--aluminum)' }}>
                      {pipeline.processed}
                    </p>
                    <p className="mono text-xs" style={{ color: 'var(--orange)' }}>
                      {pipeline.change}
                    </p>
                  </div>
                  <div className="hidden md:flex items-center gap-1 shrink-0">
                    <span className="star-rating text-sm">★</span>
                    <span className="mono text-xs font-bold" style={{ color: 'var(--aluminum)' }}>
                      {pipeline.rating}
                    </span>
                  </div>
                </div>
              ))}
            </div>
            <div className="p-4 border-t" style={{ borderColor: 'rgba(74,74,90,0.3)' }}>
              <button className="btn-secondary text-xs py-2 px-4 w-full">
                Voir Tous les 1487 Jeux de Données →
              </button>
            </div>
          </div>

          {/* Rising card */}
          <div
            className="bento-card reveal flex flex-col"
            style={{ background: 'var(--graphite)' }}
          >
            <div className="p-5 border-b" style={{ borderColor: 'rgba(74,74,90,0.4)' }}>
              <div className="flex items-center justify-between">
                <span className="mono font-bold text-sm" style={{ color: 'var(--aluminum)' }}>
                  En Hausse ↑
                </span>
                <span className="badge-orange">Croissance SdS</span>
              </div>
            </div>
            <div className="flex-1 p-5 space-y-5">
              {risingModels.map((model, i) => (
                <div
                  key={model.name}
                  className="reveal group cursor-pointer"
                  style={{ transitionDelay: `${i * 80}ms` }}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="mono font-bold text-sm" style={{ color: 'var(--aluminum)' }}>
                      {model.name}
                    </span>
                    <span className="mono font-black text-sm" style={{ color: 'var(--orange)' }}>
                      {model.growth}
                    </span>
                  </div>
                  <MiniChart bars={model.bars} />
                  <p className="mono text-xs mt-1" style={{ color: 'var(--titanium-light)' }}>
                    {model.week}
                  </p>
                </div>
              ))}
            </div>
            <div
              className="p-5 border-t mt-auto"
              style={{ borderColor: 'rgba(74,74,90,0.3)', background: 'rgba(255,107,43,0.04)' }}
            >
              <p className="mono text-xs" style={{ color: 'var(--aluminum-dim)' }}>
                <span style={{ color: 'var(--orange)' }}>Pro :</span> Suivi de précision + benchmarks de score de confiance
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
