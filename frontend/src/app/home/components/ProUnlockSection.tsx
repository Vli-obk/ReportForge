'use client';

import { useRef, useEffect, useState } from 'react';

const freeFeatures = [
  'Traiter jusqu\'à 100 PDFs/mois',
  'Extraction OCR basique',
  'Analyse de tableaux standard',
  'Export vers CSV / JSON',
  'Analytiques du tableau de bord',
];

const proFeatures = [
  'Traitement de PDFs illimité',
  'Résumé IA avancé et Insights',
  'Reconnaissance d\'Entités Nommées (REN)',
  'OCR pour écriture manuscrite et docs scannés',
  'Modèles d\'extraction personnalisés',
  'Accès API pour l\'automatisation',
  'Canal de support prioritaire',
];

const proStats = [
  { label: 'Temps moy. économisé/doc', value: '1.5h' },
  { label: 'Précision d\'extraction', value: '99%' },
  { label: 'Types de docs supportés', value: '1 240+' },
  { label: 'Utilisateurs Pro', value: '4.8k' },
];

export default function ProUnlockSection() {
  const sectionRef = useRef<HTMLDivElement>(null);
  const [submitted, setSubmitted] = useState(false);
  const [email, setEmail] = useState('');
  const [useCase, setUseCase] = useState('');

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.querySelectorAll('.reveal').forEach((el, i) => {
              setTimeout(() => el.classList.add('visible'), i * 100);
            });
          }
        });
      },
      { threshold: 0.1 }
    );
    if (sectionRef.current) observer.observe(sectionRef.current);
    return () => observer.disconnect();
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (email) setSubmitted(true);
  };

  return (
    <section id="pro" ref={sectionRef} className="py-20 px-6" style={{ background: '#0A0A18' }}>
      <div className="max-w-7xl mx-auto">
        <div className="mb-10">
          <span
            className="mono text-xs uppercase tracking-widest"
            style={{ color: 'var(--orange)' }}
          >
            // 04 — Couche Analytics Pro
          </span>
          <h2
            className="mono font-black text-3xl md:text-4xl mt-2"
            style={{ color: 'var(--aluminum)' }}
          >
            Les Données Dont Vous Avez Besoin.
          </h2>
          <p className="mt-2 text-sm" style={{ color: 'var(--aluminum-dim)' }}>
            Gratuit pour commencer. Pro vous donne l'intelligence IA pour tout automatiser.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
          {/* Free vs Pro comparison */}
          <div
            className="bento-card reveal lg:col-span-2 overflow-hidden"
            style={{ background: 'var(--graphite)' }}
          >
            <div
              className="grid grid-cols-2 divide-x"
              style={{ borderColor: 'rgba(74,74,90,0.4)' }}
            >
              {/* Free */}
              <div className="p-6">
                <div className="flex items-center gap-2 mb-5">
                  <span className="tag-pill">GRATUIT</span>
                  <span className="mono text-xs" style={{ color: 'var(--aluminum-dim)' }}>
                    Toujours
                  </span>
                </div>
                <ul className="space-y-3">
                  {freeFeatures.map((f) => (
                    <li key={f} className="flex items-start gap-2">
                      <span
                        className="mono text-xs mt-0.5"
                        style={{ color: 'var(--titanium-light)' }}
                      >
                        ✓
                      </span>
                      <span className="mono text-xs" style={{ color: 'var(--aluminum-dim)' }}>
                        {f}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
              {/* Pro */}
              <div className="p-6" style={{ background: 'rgba(255,107,43,0.04)' }}>
                <div className="flex items-center gap-2 mb-5">
                  <span className="badge-orange">PRO</span>
                  <span className="mono text-xs" style={{ color: 'var(--orange)' }}>
                    $12/mo
                  </span>
                </div>
                <ul className="space-y-3">
                  {proFeatures.map((f) => (
                    <li key={f} className="flex items-start gap-2">
                      <span className="mono text-xs mt-0.5" style={{ color: 'var(--orange)' }}>
                        ✦
                      </span>
                      <span className="mono text-xs" style={{ color: 'var(--aluminum)' }}>
                        {f}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
            {/* Pro stats row */}
            <div
              className="border-t grid grid-cols-4 divide-x"
              style={{ borderColor: 'rgba(74,74,90,0.4)' }}
            >
              {proStats.map((stat) => (
                <div key={stat.label} className="p-4 text-center">
                  <p className="mono font-black text-xl" style={{ color: 'var(--orange)' }}>
                    {stat.value}
                  </p>
                  <p
                    className="mono text-xs mt-1"
                    style={{ color: 'var(--aluminum-dim)', lineHeight: 1.3 }}
                  >
                    {stat.label}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Sign-up form */}
          <div
            className="bento-card reveal flex flex-col"
            style={{ background: 'var(--graphite)', borderColor: 'rgba(255,107,43,0.25)' }}
          >
            <div className="p-5 border-b" style={{ borderColor: 'rgba(74,74,90,0.4)' }}>
              <p className="mono font-black text-base" style={{ color: 'var(--aluminum)' }}>
                Démarrer l'Essai Pro
              </p>
              <p className="mono text-xs mt-1" style={{ color: 'var(--aluminum-dim)' }}>
                14 jours gratuits. Sans carte bancaire.
              </p>
            </div>
            <div className="flex-1 p-5">
              {submitted ? (
                <div className="h-full flex flex-col items-center justify-center text-center gap-3">
                  <div
                    className="w-12 h-12 rounded-full flex items-center justify-center text-2xl"
                    style={{
                      background: 'rgba(255,107,43,0.15)',
                      border: '1px solid rgba(255,107,43,0.4)',
                    }}
                  >
                    ✓
                  </div>
                  <p className="mono font-bold text-sm" style={{ color: 'var(--orange)' }}>
                    C'est parti.
                  </p>
                  <p className="mono text-xs" style={{ color: 'var(--aluminum-dim)' }}>
                    Vérifiez votre boîte mail — lien d'accès Pro en route.
                  </p>
                </div>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div>
                    <label
                      className="mono text-xs uppercase tracking-widest block mb-2"
                      style={{ color: 'var(--aluminum-dim)' }}
                    >
                      Email
                    </label>

                    <input
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="you@company.com"
                      className="input-field"
                    />
                  </div>
                  <div>
                    <label
                      className="mono text-xs uppercase tracking-widest block mb-2"
                      style={{ color: 'var(--aluminum-dim)' }}
                    >
                      Cas d'Usage Principal
                    </label>
                    <div className="relative">
                      <select
                        required
                        value={useCase}
                        onChange={(e) => setUseCase(e.target.value)}
                        className="select-field"
                      >
                        <option value="">Sélectionner</option>
                        <option value="data-analyst">Analyste de Données</option>
                        <option value="finance">Équipe Finance</option>
                        <option value="operations">Opérations / Juridique</option>
                      </select>
                      <span
                        className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none mono text-xs"
                        style={{ color: 'var(--titanium-light)' }}
                      >
                        ▼
                      </span>
                    </div>
                  </div>
                  <button type="submit" className="btn-primary w-full py-3">
                    Démarrer l'Essai Pro — 14 Jours
                  </button>
                  <p
                    className="mono text-xs text-center"
                    style={{ color: 'var(--titanium-light)' }}
                  >
                    Sans CB · Annuler à tout moment · Accès immédiat
                  </p>
                </form>
              )}
            </div>
            <div
              className="p-4 border-t"
              style={{ borderColor: 'rgba(74,74,90,0.3)', background: 'rgba(255,107,43,0.03)' }}
            >
              <p className="mono text-xs" style={{ color: 'var(--aluminum-dim)' }}>
                4 800+ équipes déjà sur Pro. Note moyenne :{' '}
                <span style={{ color: 'var(--orange)' }}>★ 4.9</span>
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
