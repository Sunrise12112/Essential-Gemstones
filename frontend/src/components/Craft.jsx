import React from 'react';
import { craftSteps, craftImage } from '../mock';

export default function Craft() {
  return (
    <section className="py-24 md:py-32 bg-[#faf6f0]">
      <div className="max-w-7xl mx-auto px-6 md:px-10 grid lg:grid-cols-2 gap-12 lg:gap-20 items-start">
        <div className="lg:sticky lg:top-28">
          <p className="text-xs tracking-[0.3em] uppercase text-[#8b6b4f] mb-4">Craftsmanship</p>
          <h2 className="font-serif text-4xl md:text-5xl text-[#1a1410] mb-6 leading-tight">What Goes Into <span className="italic">Every Bracelet</span></h2>
          <p className="text-[#5a4a3d] leading-relaxed mb-8">From material selection to final packaging, every step is approached with care and quality. Here&rsquo;s what you can expect when you shop with Essential Gemstones.</p>
          <div className="aspect-[5/4] rounded-3xl overflow-hidden">
            <img src={craftImage} alt="Jewelry making process" className="w-full h-full object-cover" />
          </div>
        </div>

        <div className="space-y-8">
          {craftSteps.map((step, i) => (
            <div key={i} className="group p-8 bg-[#f3ece0] rounded-2xl border border-[#e8dfd1] hover:bg-[#ede2d0] transition-colors">
              <div className="flex items-start gap-6">
                <span className="font-serif text-5xl text-[#c9a876] leading-none">{step.number}</span>
                <div>
                  <h3 className="font-serif text-2xl text-[#1a1410] mb-3">{step.title}</h3>
                  <p className="text-[#5a4a3d] leading-relaxed">{step.desc}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
