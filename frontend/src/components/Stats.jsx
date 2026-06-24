import React from 'react';
import { useSite } from '../context/SiteContext';

export default function Stats() {
  const { site } = useSite();
  const s = site.stats || {};
  const items = s.items || [];
  return (
    <section className="py-24 md:py-28 bg-[#faf6f0]">
      <div className="max-w-7xl mx-auto px-6 md:px-10">
        <div className="text-center mb-14">
          {s.kicker && <p className="text-xs tracking-[0.3em] uppercase text-[#8b6b4f] mb-4">{s.kicker}</p>}
          {s.title && <h2 className="font-serif text-4xl md:text-5xl text-[#1a1410] leading-tight">{s.title}</h2>}
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 md:gap-8">
          {items.map((it, i) => (
            <div key={i} className="text-center px-5 py-10 bg-[#f3ece0] rounded-2xl border border-[#e8dfd1] hover:bg-[#ede2d0] transition-colors">
              <div className="font-serif text-5xl md:text-6xl text-[#6b4f3a] mb-3">{it.number}</div>
              <div className="text-sm tracking-[0.2em] uppercase text-[#1a1410] mb-3">{it.label}</div>
              <p className="text-xs md:text-sm text-[#5a4a3d] leading-relaxed">{it.sub}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
