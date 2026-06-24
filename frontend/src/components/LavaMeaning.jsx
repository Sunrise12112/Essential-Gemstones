import React from 'react';
import { Mountain, Flame, Leaf, Shield, Sparkles, Heart, Lightbulb, Star, Gem } from 'lucide-react';
import { useSite } from '../context/SiteContext';

const ICONS = { Mountain, Flame, Leaf, Shield, Sparkles, Heart, Lightbulb, Star, Gem };

export default function LavaMeaning() {
  const { site } = useSite();
  const l = site.lavaMeaning || {};
  const items = l.items || [];
  return (
    <section className="py-24 md:py-32 bg-[#1a1410] text-[#faf6f0] relative">
      <div className="max-w-7xl mx-auto px-6 md:px-10">
        <div className="text-center mb-16 max-w-3xl mx-auto">
          {l.kicker && <p className="text-xs tracking-[0.3em] uppercase text-[#c9a876] mb-4">{l.kicker}</p>}
          {l.title && <h2 className="font-serif text-4xl md:text-5xl mb-5 leading-tight">{l.title}</h2>}
          {l.subtitle && <p className="text-[#d4c5af] leading-relaxed">{l.subtitle}</p>}
        </div>
        <div className="grid md:grid-cols-2 gap-6 md:gap-8">
          {items.map((m, i) => {
            const Icon = ICONS[m.icon] || Sparkles;
            return (
              <div key={i} className="group p-8 md:p-10 rounded-3xl border border-[#3d2f24] hover:border-[#c9a876]/50 hover:bg-[#241b15] transition-all duration-500">
                <Icon className="w-8 h-8 text-[#c9a876] mb-6" />
                <h3 className="font-serif text-2xl md:text-3xl mb-4">{m.title}</h3>
                <p className="text-[#bfae95] leading-relaxed">{m.desc}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
