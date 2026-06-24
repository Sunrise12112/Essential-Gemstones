import React from 'react';
import { Crown, Gift, Star, MessageCircle, Heart, Sparkles, Gem } from 'lucide-react';
import { useSite } from '../context/SiteContext';

const ICONS = { Gift, Star, MessageCircle, Heart, Sparkles, Gem, Crown };

export default function VIP() {
  const { site } = useSite();
  const v = site.vip || {};
  const perks = v.perks || [];
  return (
    <section className="py-24 md:py-32 bg-[#2c2420] text-[#faf6f0] relative overflow-hidden">
      <div className="absolute inset-0 opacity-10" style={{ background: 'radial-gradient(circle at 50% 0%, #c9a876 0%, transparent 60%)' }}></div>
      <div className="relative max-w-5xl mx-auto px-6 md:px-10 text-center">
        <Crown className="w-10 h-10 mx-auto mb-5 text-[#c9a876]" />
        {v.kicker && <p className="text-xs tracking-[0.3em] uppercase text-[#c9a876] mb-4">{v.kicker}</p>}
        {v.title && <h2 className="font-serif text-4xl md:text-5xl lg:text-6xl mb-6 leading-tight">{v.title}</h2>}
        {v.subtitle && <p className="text-[#d4c5af] max-w-2xl mx-auto leading-relaxed mb-10 text-lg">{v.subtitle}</p>}
        {perks.length > 0 && (
          <div className="grid sm:grid-cols-3 gap-5 max-w-3xl mx-auto mb-12">
            {perks.map((p, i) => {
              const Icon = ICONS[p.icon] || Gift;
              return (
                <div key={i} className="p-6 border border-[#3d2f24] rounded-2xl">
                  <Icon className="w-6 h-6 text-[#c9a876] mx-auto mb-3" />
                  <p className="text-sm text-[#d4c5af]">{p.label}</p>
                </div>
              );
            })}
          </div>
        )}
        {v.ctaLabel && (
          <a href={v.ctaUrl || '#'} target="_blank" rel="noreferrer" className="inline-block px-9 py-4 bg-[#c9a876] text-[#1a1410] rounded-full text-sm tracking-wider uppercase font-medium hover:bg-[#d6b885] transition-colors">{v.ctaLabel}</a>
        )}
      </div>
    </section>
  );
}
