import React from 'react';
import { lavaMeanings } from '../mock';
import { Mountain, Flame, Leaf, Shield } from 'lucide-react';

const iconMap = { Mountain, Flame, Leaf, Shield };

export default function LavaMeaning() {
  return (
    <section className="py-24 md:py-32 bg-[#1a1410] text-[#faf6f0] relative">
      <div className="max-w-7xl mx-auto px-6 md:px-10">
        <div className="text-center mb-16 max-w-3xl mx-auto">
          <p className="text-xs tracking-[0.3em] uppercase text-[#c9a876] mb-4">The Power Within</p>
          <h2 className="font-serif text-4xl md:text-5xl mb-5 leading-tight">What Lava Stone <span className="italic">Means</span></h2>
          <p className="text-[#d4c5af] leading-relaxed">More than a material — lava stone is a symbol, a history, and an energy all its own.</p>
        </div>

        <div className="grid md:grid-cols-2 gap-6 md:gap-8">
          {lavaMeanings.map((m, i) => {
            const Icon = iconMap[m.icon];
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
