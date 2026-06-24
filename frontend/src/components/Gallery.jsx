import React from 'react';
import { useSite } from '../context/SiteContext';
import { resolveMediaUrl } from '../lib/api';

export default function Gallery() {
  const { site } = useSite();
  const g = site.gallery || {};
  const images = g.images || [];
  return (
    <section className="py-24 md:py-32 bg-[#faf6f0]">
      <div className="max-w-7xl mx-auto px-6 md:px-10">
        <div className="text-center mb-14">
          {g.kicker && <p className="text-xs tracking-[0.3em] uppercase text-[#8b6b4f] mb-4">{g.kicker}</p>}
          {g.title && <h2 className="font-serif text-4xl md:text-5xl text-[#1a1410] leading-tight">{g.title}</h2>}
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-5">
          {images.map((img, i) => (
            <div key={i} className="group relative aspect-[3/4] overflow-hidden rounded-2xl bg-[#e8dfd1]">
              <img src={resolveMediaUrl(img)} alt={`Gallery ${i+1}`} className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700" />
              <div className="absolute inset-0 bg-[#1a1410]/0 group-hover:bg-[#1a1410]/15 transition-colors"></div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
