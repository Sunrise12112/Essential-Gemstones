import React from 'react';
import { useSite } from '../context/SiteContext';
import { resolveMediaUrl } from '../lib/api';

export default function Story() {
  const { site } = useSite();
  const s = site.story || {};
  const paragraphs = s.paragraphs || [];
  return (
    <section id="story" className="py-24 md:py-32 bg-[#faf6f0]">
      <div className="max-w-7xl mx-auto px-6 md:px-10 grid lg:grid-cols-2 gap-12 lg:gap-20 items-center">
        <div className="relative order-2 lg:order-1">
          <div className="aspect-[4/5] rounded-3xl overflow-hidden bg-[#e8dfd1]">
            {s.image && <img src={resolveMediaUrl(s.image)} alt={s.title} className="w-full h-full object-cover" />}
          </div>
          {s.badge && (
            <div className="absolute -top-6 -right-6 hidden md:block bg-[#6b4f3a] text-[#faf6f0] px-7 py-6 rounded-2xl max-w-[200px]">
              <p className="font-serif italic text-lg leading-snug">{s.badge}</p>
            </div>
          )}
        </div>
        <div className="order-1 lg:order-2">
          {s.kicker && <p className="text-xs tracking-[0.3em] uppercase text-[#8b6b4f] mb-4">{s.kicker}</p>}
          {s.title && <h2 className="font-serif text-4xl md:text-5xl text-[#1a1410] mb-8 leading-tight">{s.title}</h2>}
          <div className="space-y-5 text-[#3d3128] leading-relaxed">
            {paragraphs.map((p, i) => <p key={i}>{p}</p>)}
          </div>
        </div>
      </div>
    </section>
  );
}
