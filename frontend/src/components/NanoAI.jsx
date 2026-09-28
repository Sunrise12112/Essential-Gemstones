import React from 'react';
import { Sparkles, ArrowUpRight, Brain, Layers, Wand2, Gift } from 'lucide-react';
import { useSite } from '../context/SiteContext';
import { resolveMediaUrl } from '../lib/api';

const ICONS = [Brain, Layers, Wand2, Gift];

export default function NanoAI() {
  const { site } = useSite();
  const n = site.nanoAI || {};
  const features = n.features || [];

  return (
    <section id="nano-ai" data-testid="nano-ai-section" className="py-24 md:py-32 bg-[#1a1410] text-[#faf6f0] overflow-hidden">
      <div className="max-w-7xl mx-auto px-6 md:px-10">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
          {/* Copy */}
          <div>
            {n.kicker && <p data-testid="nano-ai-kicker" className="text-xs tracking-[0.3em] uppercase text-[#c9a876] mb-4">{n.kicker}</p>}
            {n.title && <h2 data-testid="nano-ai-title" className="font-serif text-4xl sm:text-5xl lg:text-6xl leading-[1.05] mb-6">{n.title}</h2>}
            {n.subtitle && <p data-testid="nano-ai-subtitle" className="text-base md:text-lg text-[#d4c5af] leading-relaxed mb-8 max-w-xl">{n.subtitle}</p>}

            {features.length > 0 && (
              <div className="grid sm:grid-cols-2 gap-4 mb-9">
                {features.map((f, i) => {
                  const Icon = ICONS[i % ICONS.length];
                  return (
                    <div key={i} data-testid={`nano-ai-feature-${i}`} className="flex items-start gap-3">
                      <span className="w-9 h-9 shrink-0 rounded-full bg-[#c9a876]/15 border border-[#c9a876]/30 flex items-center justify-center">
                        <Icon className="w-4 h-4 text-[#c9a876]" />
                      </span>
                      <div>
                        <p className="text-sm font-medium text-[#faf6f0]">{f.title}</p>
                        {f.desc && <p className="text-xs text-[#a9977f] leading-relaxed mt-0.5">{f.desc}</p>}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            <div className="flex flex-wrap items-center gap-4">
              {n.ctaLabel && n.ctaUrl && (
                <a
                  href={n.ctaUrl}
                  target="_blank"
                  rel="noreferrer"
                  data-testid="nano-ai-cta"
                  className="inline-flex items-center gap-2 px-7 py-4 bg-[#c9a876] text-[#1a1410] rounded-full text-sm tracking-wider uppercase font-medium hover:bg-[#d6b885] transition-colors"
                >
                  {n.ctaLabel} <ArrowUpRight className="w-4 h-4" />
                </a>
              )}
              {n.note && (
                <span className="inline-flex items-center gap-1.5 text-xs text-[#a9977f]">
                  <Sparkles className="w-3.5 h-3.5 text-[#c9a876]" /> {n.note}
                </span>
              )}
            </div>
          </div>

          {/* Image */}
          {n.image && (
            <div className="relative">
              <div className="absolute -inset-6 bg-[#c9a876]/10 blur-3xl rounded-full" aria-hidden="true" />
              <div className="relative rounded-3xl overflow-hidden border border-[#3d2f24] shadow-2xl">
                <img
                  src={resolveMediaUrl(n.image)}
                  alt={n.title || 'Nano AI'}
                  data-testid="nano-ai-image"
                  className="w-full h-full object-cover aspect-[4/3]"
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
