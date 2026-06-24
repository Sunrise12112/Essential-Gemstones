import React from 'react';
import { Sparkles, Heart, Lightbulb, Star, Gem, Flame, Leaf, Shield } from 'lucide-react';
import { useSite } from '../context/SiteContext';
import { resolveMediaUrl } from '../lib/api';

const ICONS = { Sparkles, Heart, Lightbulb, Star, Gem, Flame, Leaf, Shield };

export default function Founder() {
  const { site } = useSite();
  const f = site.founder || {};
  const blocks = f.blocks || [];
  return (
    <section id="founder" className="py-24 md:py-32 bg-[#f3ece0]">
      <div className="max-w-7xl mx-auto px-6 md:px-10 grid lg:grid-cols-5 gap-12 lg:gap-16 items-center">
        <div className="lg:col-span-2 relative">
          <div className="aspect-square rounded-full overflow-hidden border-8 border-[#faf6f0] shadow-xl bg-[#e8dfd1]">
            {f.image && <img src={resolveMediaUrl(f.image)} alt={f.title} className="w-full h-full object-cover" />}
          </div>
          {(f.ageBadge || f.ageLabel) && (
            <div className="absolute -bottom-3 -right-3 bg-[#1a1410] text-[#c9a876] w-28 h-28 rounded-full flex flex-col items-center justify-center text-center p-2">
              {f.ageBadge && <span className="font-serif text-3xl leading-none">{f.ageBadge}</span>}
              {f.ageLabel && <span className="text-[10px] tracking-[0.2em] uppercase mt-1">{f.ageLabel}</span>}
            </div>
          )}
        </div>
        <div className="lg:col-span-3">
          {f.kicker && <p className="text-xs tracking-[0.3em] uppercase text-[#8b6b4f] mb-4">{f.kicker}</p>}
          {f.title && <h2 className="font-serif text-4xl md:text-5xl text-[#1a1410] mb-6 leading-tight">{f.title}</h2>}
          {f.intro && <p className="text-[#3d3128] leading-relaxed mb-6">{f.intro}</p>}
          <div className="space-y-5">
            {blocks.map((b, i) => {
              const Icon = ICONS[b.icon] || Sparkles;
              return (
                <div key={i} className="flex gap-4">
                  <Icon className="w-5 h-5 text-[#6b4f3a] mt-1 shrink-0" />
                  <div>
                    <h4 className="font-serif text-lg text-[#1a1410] mb-1">{b.title}</h4>
                    <p className="text-sm text-[#5a4a3d] leading-relaxed">{b.desc}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
