import React from 'react';
import { ArrowDown } from 'lucide-react';
import { heroImage } from '../mock';

export default function Hero() {
  return (
    <section id="top" className="relative min-h-screen flex items-center overflow-hidden bg-[#faf6f0]">
      {/* Left content */}
      <div className="relative z-10 max-w-7xl mx-auto w-full px-6 md:px-10 pt-32 pb-20 grid lg:grid-cols-2 gap-12 items-center">
        <div className="fade-up">
          <p className="text-xs tracking-[0.3em] uppercase text-[#8b6b4f] mb-6">Handmade · Volcanic · Intentional</p>
          <h1 className="font-serif text-5xl md:text-6xl lg:text-7xl leading-[1.05] text-[#1a1410] mb-6">
            Essential<br />
            <span className="italic font-light">Gemstones</span>
          </h1>
          <p className="text-lg md:text-xl text-[#5a4a3d] max-w-xl mb-10 leading-relaxed">
            Handmade lava stone bracelets inspired by nature and strength. Born from fire, shaped by hand — each piece carries a quiet story you can wear.
          </p>
          <div className="flex flex-wrap items-center gap-4">
            <a href="#shop" className="px-8 py-4 bg-[#1a1410] text-[#faf6f0] rounded-full text-sm tracking-wider uppercase hover:bg-[#6b4f3a] transition-colors">Shop the Collection</a>
            <a href="#story" className="px-8 py-4 border border-[#3d3128] text-[#3d3128] rounded-full text-sm tracking-wider uppercase hover:bg-[#3d3128] hover:text-[#faf6f0] transition-colors">Our Story</a>
          </div>
        </div>

        {/* Right image */}
        <div className="relative h-[420px] md:h-[560px] lg:h-[640px] fade-up" style={{ animationDelay: '0.2s' }}>
          <div className="absolute inset-0 rounded-[280px] overflow-hidden border border-[#d4c5af]/60">
            <img src={heroImage} alt="Volcanic stone landscape" className="w-full h-full object-cover" />
            <div className="absolute inset-0 bg-gradient-to-b from-[#1a1410]/20 via-transparent to-[#1a1410]/40"></div>
          </div>
          <div className="absolute -bottom-6 -left-6 md:-left-12 bg-[#faf6f0] px-6 py-5 shadow-xl rounded-2xl max-w-[240px] float-anim">
            <p className="font-serif italic text-[#6b4f3a] text-sm leading-relaxed">&ldquo;What we wear can carry meaning.&rdquo;</p>
            <p className="text-xs text-[#8b6b4f] mt-2 tracking-wider">— LUCA, FOUNDER</p>
          </div>
        </div>
      </div>

      <a href="#shop" className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 text-[#8b6b4f] hover:text-[#2c2420] transition-colors">
        <span className="text-[10px] tracking-[0.3em] uppercase">Explore</span>
        <ArrowDown className="w-4 h-4 animate-bounce" />
      </a>
    </section>
  );
}
