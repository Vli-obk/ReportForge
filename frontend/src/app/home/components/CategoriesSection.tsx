'use client';

import { useEffect, useRef } from 'react';

const categories = [
  {
    id: 'invoices',
    label: 'Factures',
    count: 452,
    rating: 4.9,
    topPlugin: 'Line Item Extractor',
    icon: '⬛',
    description: 'Lignes détaillées, totaux, détails fournisseur, montants de taxes',
    color: 'rgba(255,107,43,0.08)',
    borderColor: 'rgba(255,107,43,0.25)',
  },
  {
    id: 'receipts',
    label: 'Reçus',
    count: 328,
    rating: 4.8,
    topPlugin: 'OCR Scanner',
    icon: '◈',
    description: 'Montants, dates, catégorisation marchande',
    color: 'rgba(74,74,90,0.15)',
    borderColor: 'rgba(74,74,90,0.4)',
  },
  {
    id: 'contracts',
    label: 'Contrats',
    count: 184,
    rating: 4.7,
    topPlugin: 'Entity Parser',
    icon: '◉',
    description: "Clauses, signatures, extraction d'entités nommées",
    color: 'rgba(74,74,90,0.15)',
    borderColor: 'rgba(74,74,90,0.4)',
  },
  {
    id: 'financials',
    label: 'Finances',
    count: 684,
    rating: 4.9,
    topPlugin: 'Table Extractor',
    icon: '▦',
    description: 'Bilans, comptes de résultats, données tabulaires complexes',
    color: 'rgba(255,107,43,0.08)',
    borderColor: 'rgba(255,107,43,0.25)',
  },
  {
    id: 'healthcare',
    label: 'Santé',
    count: 215,
    rating: 4.6,
    topPlugin: 'HIPAA Redact',
    icon: '◧',
    description: 'Dossiers patients, analyse de résultats de labo, rédaction',
    color: 'rgba(74,74,90,0.15)',
    borderColor: 'rgba(74,74,90,0.4)',
  },
  {
    id: 'logistics',
    label: 'Logistique',
    count: 163,
    rating: 4.8,
    topPlugin: 'Waybill Reader',
    icon: '◫',
    description: "Étiquettes d'expédition, manifestes, extraction de suivi",
    color: 'rgba(74,74,90,0.15)',
    borderColor: 'rgba(74,74,90,0.4)',
  },
];

function StarRating({ rating }: { rating: number }) {
  const full = Math.floor(rating);
  const hasHalf = rating % 1 >= 0.5;
  return (
    <span className="star-rating">
      {'★'.repeat(full)}
      {hasHalf ? '½' : ''}
      {'☆'.repeat(5 - full - (hasHalf ? 1 : 0))}
      <span
        className="ml-1 text-xs"
        style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono' }}
      >
        {rating.toFixed(1)}
      </span>
    </span>
  );
}

export default function CategoriesSection() {
  const sectionRef = useRef<HTMLDivElement>(null);
  const cardsRef = useRef<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
          }
        });
      },
      { threshold: 0.1 }
    );

    cardsRef.current.forEach((card) => {
      if (card) observer.observe(card);
    });

    return () => observer.disconnect();
  }, []);

  return (
    <section id="categories" className="py-20 px-6" style={{ background: 'var(--carbon)' }}>
      <div className="max-w-7xl mx-auto">
        {/* Section header */}
        <div className="flex items-end justify-between mb-10">
          <div>
            <span
              className="mono text-xs uppercase tracking-widest"
              style={{ color: 'var(--orange)' }}
            >
              // 01 — Types de Documents
            </span>
            <h2
              className="mono font-black text-3xl md:text-4xl mt-2"
              style={{ color: 'var(--aluminum)' }}
            >
              Tout Type de Document.
            </h2>
            <p className="mt-2 text-sm" style={{ color: 'var(--aluminum-dim)' }}>
              Conçu pour chaque secteur. 99% de précision d'extraction pour tous les types de documents.
            </p>
          </div>
          <span className="badge-orange hidden md:inline-flex">
            {categories.reduce((s, c) => s + c.count, 0)}k+ traités au total
          </span>
        </div>

        {/* Bento grid */}
        <div
          className="grid gap-3"
          style={{
            gridTemplateColumns: 'repeat(6, 1fr)',
            gridTemplateRows: 'auto',
          }}
        >
          {/* Large card — CMS (most plugins) */}
          <div
            ref={(el) => {
              cardsRef.current[0] = el;
            }}
            className="bento-card reveal col-span-6 md:col-span-2 md:row-span-2 p-6 flex flex-col justify-between cursor-pointer group"
            style={{
              background: categories[3].color,
              borderColor: categories[3].borderColor,
              minHeight: '240px',
            }}
          >
            <div className="flex items-start justify-between">
              <div>
                <span className="badge-orange">LE PLUS TRAITÉ</span>
                <p
                  className="mono font-black mt-3"
                  style={{ fontSize: '4rem', lineHeight: 1, color: 'var(--aluminum)' }}
                >
                  {categories[3].count}k
                </p>
              </div>
              <span className="text-4xl opacity-40" style={{ fontFamily: 'monospace' }}>
                {categories[3].icon}
              </span>
            </div>
            <div>
              <p className="mono font-bold text-xl" style={{ color: 'var(--aluminum)' }}>
                {categories[3].label}
              </p>
              <p className="text-sm mt-1" style={{ color: 'var(--aluminum-dim)' }}>
                {categories[3].description}
              </p>
              <div className="flex items-center justify-between mt-4">
                <StarRating rating={categories[3].rating} />
                <span className="mono text-xs" style={{ color: 'var(--aluminum-dim)' }}>
                  Meilleur Modèle : {categories[3].topPlugin}
                </span>
              </div>
              <div className="progress-bar mt-3">
                <div
                  className="progress-bar-fill"
                  style={{ width: `${(categories[3].count / 100) * 100}%` }}
                />
              </div>
            </div>
          </div>

          {/* Remaining 5 categories */}
          {[categories[0], categories[2], categories[1], categories[4], categories[5]].map(
            (cat, i) => (
              <div
                key={cat.id}
                ref={(el) => {
                  cardsRef.current[i + 1] = el;
                }}
                className="bento-card reveal col-span-6 md:col-span-2 p-5 flex flex-col justify-between cursor-pointer group"
                style={{
                  background: cat.color,
                  borderColor: cat.borderColor,
                  transitionDelay: `${i * 80}ms`,
                  minHeight: '150px',
                }}
              >
                <div className="flex items-start justify-between">
                  <span className="tag-pill">{cat.label}</span>
                  <span className="mono font-black text-2xl" style={{ color: 'var(--aluminum)' }}>
                    {cat.count}k
                  </span>
                </div>
                <div>
                  <p className="text-xs mt-2 mb-3" style={{ color: 'var(--aluminum-dim)' }}>
                    {cat.description}
                  </p>
                  <div className="flex items-center justify-between">
                    <StarRating rating={cat.rating} />
                    <span className="mono text-xs" style={{ color: 'var(--titanium-light)' }}>
                      {cat.topPlugin}
                    </span>
                  </div>
                </div>
              </div>
            )
          )}
        </div>
      </div>
    </section>
  );
}
