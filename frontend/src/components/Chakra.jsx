import React from 'react';
import { chakraStones } from '../mock';
import { Droplet } from 'lucide-react';

export default function Chakra() {
  return (
    <section id="chakra" className="py-24 md:py-32 bg-[#f3ece0]">
      <div className="max-w-7xl mx-auto px-6 md:px-10">
        <div className="text-center mb-16 max-w-3xl mx-auto">
          <p className="text-xs tracking-[0.3em] uppercase text-[#8b6b4f] mb-4">Our Craft</p>
          <h2 className="font-serif text-4xl md:text-5xl text-[#1a1410] mb-5 leading-tight">Awaken Your Spirit: <span className="italic">The 7 Chakra Bracelet</span></h2>
          <p className="text-[#5a4a3d] leading-relaxed">Embrace balance and harmony with our handcrafted 7 Chakra Lava Stone Bracelet. Each stone is carefully selected to align with your energy centers, while lava stone beads offer a unique way to diffuse essential oils.</p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {chakraStones.map((s, i) => (
            <div key={i} className="group bg-[#faf6f0] p-7 rounded-2xl border border-[#e8dfd1] hover:-translate-y-1 hover:shadow-lg transition-all duration-500">
              <div className="w-12 h-12 rounded-full mb-5 shadow-inner" style={{ background: `radial-gradient(circle at 30% 30%, ${s.color}cc, ${s.color})` }}></div>
              <h3 className="font-serif text-xl text-[#1a1410] mb-1">{s.stone}</h3>
              <p className="text-xs tracking-[0.2em] uppercase text-[#8b6b4f] mb-3">{s.chakra}</p>
              <p className="text-sm text-[#5a4a3d] leading-relaxed">{s.desc}</p>
            </div>
          ))}
        </div>

        <div className="mt-14 max-w-3xl mx-auto bg-[#faf6f0] border border-[#e8dfd1] rounded-2xl p-6 md:p-8 flex items-start gap-4">
          <Droplet className="w-5 h-5 text-[#6b4f3a] mt-1 shrink-0" />
          <p className="text-[#3d3128] leading-relaxed text-sm md:text-base">
            Each stone works in harmony, aligning your chakras from root to crown. Simply add a drop of your favorite essential oil to the lava beads for an aromatic experience that complements your journey.
          </p>
        </div>
      </div>
    </section>
  );
}
