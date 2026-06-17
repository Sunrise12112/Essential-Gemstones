import React from 'react';
import { storyImage } from '../mock';

export default function Story() {
  return (
    <section id="story" className="py-24 md:py-32 bg-[#faf6f0]">
      <div className="max-w-7xl mx-auto px-6 md:px-10 grid lg:grid-cols-2 gap-12 lg:gap-20 items-center">
        <div className="relative order-2 lg:order-1">
          <div className="aspect-[4/5] rounded-3xl overflow-hidden">
            <img src={storyImage} alt="Lava stone bracelets on table" className="w-full h-full object-cover" />
          </div>
          <div className="absolute -top-6 -right-6 hidden md:block bg-[#6b4f3a] text-[#faf6f0] px-7 py-6 rounded-2xl max-w-[200px]">
            <p className="font-serif italic text-lg leading-snug">One bracelet at a time.</p>
          </div>
        </div>

        <div className="order-1 lg:order-2">
          <p className="text-xs tracking-[0.3em] uppercase text-[#8b6b4f] mb-4">Our Story</p>
          <h2 className="font-serif text-4xl md:text-5xl text-[#1a1410] mb-8 leading-tight">Born from the Earth, <span className="italic">Made by Hand</span></h2>
          <div className="space-y-5 text-[#3d3128] leading-relaxed">
            <p>Essential Gemstones was born from a deep reverence for the natural world — its raw textures, ancient rhythms, and quiet power. Founded by <strong className="text-[#1a1410]">Luca</strong>, this small, intentional brand exists at the intersection of craftsmanship and crystal energy.</p>
            <p>Every bracelet begins as a vision and ends as something you can feel against your skin — grounding, warm, and alive. No mass production. No shortcuts. Just thoughtful, handcrafted jewelry made one bracelet at a time.</p>
            <p>Lava stone — the cornerstone of every Essential Gemstones design — is one of the oldest and most powerful stones on earth. Formed in fire and shaped by nature over thousands of years, it carries the energy of transformation, grounding, and raw strength.</p>
          </div>
        </div>
      </div>
    </section>
  );
}
