import React from 'react';
import { Droplet } from 'lucide-react';
import { useSite } from '../context/SiteContext';

export default function Chakra() {
  const { site } = useSite();
  const c = site.chakra || {};
  const stones = c.stones || [];
  return (
    <section id="chakra" className="py-24 md:py-32 bg-[#f3ece0]">
      <div className="max-w-7xl mx-auto px-6 md:px-10">
        <div className="text-center mb-16 max-w-3xl mx-auto">
          {c.kicker && <p className="text-xs tracking-[0.3em] uppercase text-[#8b6b4f] mb-4">{c.kicker}</p>}
          {c.title && <h2 className="font-serif text-4xl md:text-5xl text-[#1a1410] mb-5 leading-tight">{c.title}</h2>}
          {c.subtitle && <p className="text-[#5a4a3d] leading-relaxed">{c.subtitle}</p>}
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {stones.map((s, i) => (
            <div key={i} className="group bg-[#faf6f0] p-7 rounded-2xl border border-[#e8dfd1] hover:-translate-y-1 hover:shadow-lg transition-all duration-500">
              <div className="w-12 h-12 rounded-full mb-5 shadow-inner" style={{ background: `radial-gradient(circle at 30% 30%, ${s.color}cc, ${s.color})` }}></div>
              <h3 className="font-serif text-xl text-[#1a1410] mb-1">{s.stone}</h3>
              <p className="text-xs tracking-[0.2em] uppercase text-[#8b6b4f] mb-3">{s.chakra}</p>
              <p className="text-sm text-[#5a4a3d] leading-relaxed">{s.desc}</p>
            </div>
          ))}
        </div>
        {c.footer && (
          <div className="mt-14 max-w-3xl mx-auto bg-[#faf6f0] border border-[#e8dfd1] rounded-2xl p-6 md:p-8 flex items-start gap-4">
            <Droplet className="w-5 h-5 text-[#6b4f3a] mt-1 shrink-0" />
            <p className="text-[#3d3128] leading-relaxed text-sm md:text-base">{c.footer}</p>
          </div>
        )}
      </div>
    </section>
  );
}
