import React from 'react';
import { ShieldCheck } from 'lucide-react';

export default function Promise() {
  return (
    <section className="py-20 bg-[#2c2420] text-[#faf6f0] relative overflow-hidden">
      <div className="absolute inset-0 opacity-[0.04]" style={{
        backgroundImage: 'radial-gradient(circle at 20% 30%, #c9a876 0, transparent 50%), radial-gradient(circle at 80% 70%, #c9a876 0, transparent 50%)'
      }}></div>
      <div className="relative max-w-5xl mx-auto px-6 md:px-10 text-center">
        <ShieldCheck className="w-10 h-10 mx-auto mb-5 text-[#c9a876]" />
        <p className="text-xs tracking-[0.3em] uppercase text-[#c9a876] mb-4">Our Promise</p>
        <h2 className="font-serif text-3xl md:text-4xl lg:text-5xl mb-6 leading-tight">Why Choose <span className="italic">Essential Gemstones</span>?</h2>
        <p className="text-[#d4c5af] max-w-3xl mx-auto leading-relaxed text-lg">
          We want your bracelet to be a cherished companion for years to come. That’s why every Essential Gemstones package includes <span className="text-[#c9a876]">extra beads</span> and a <span className="text-[#c9a876]">sturdy elastic band</span> — your beloved piece is fully restringable, empowering you to easily repair or customize it yourself, right at home.
        </p>
      </div>
    </section>
  );
}
