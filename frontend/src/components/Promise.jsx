import React from 'react';
import { ShieldCheck } from 'lucide-react';
import { useSite } from '../context/SiteContext';

export default function Promise() {
  const { site } = useSite();
  const p = site.promise || {};
  return (
    <section className="py-20 bg-[#2c2420] text-[#faf6f0] relative overflow-hidden">
      <div className="absolute inset-0 opacity-[0.04]" style={{ background: 'radial-gradient(circle at 20% 30%, #c9a876 0, transparent 50%), radial-gradient(circle at 80% 70%, #c9a876 0, transparent 50%)' }}></div>
      <div className="relative max-w-5xl mx-auto px-6 md:px-10 text-center">
        <ShieldCheck className="w-10 h-10 mx-auto mb-5 text-[#c9a876]" />
        {p.kicker && <p className="text-xs tracking-[0.3em] uppercase text-[#c9a876] mb-4">{p.kicker}</p>}
        {p.title && <h2 className="font-serif text-3xl md:text-4xl lg:text-5xl mb-6 leading-tight">{p.title}</h2>}
        {p.body && <p className="text-[#d4c5af] max-w-3xl mx-auto leading-relaxed text-lg">{p.body}</p>}
      </div>
    </section>
  );
}
