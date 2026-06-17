import React from 'react';
import { founderImage } from '../mock';
import { Sparkles, Heart, Lightbulb } from 'lucide-react';

export default function Founder() {
  return (
    <section id="founder" className="py-24 md:py-32 bg-[#f3ece0]">
      <div className="max-w-7xl mx-auto px-6 md:px-10 grid lg:grid-cols-5 gap-12 lg:gap-16 items-center">
        <div className="lg:col-span-2 relative">
          <div className="aspect-square rounded-full overflow-hidden border-8 border-[#faf6f0] shadow-xl">
            <img src={founderImage} alt="Founder Luca" className="w-full h-full object-cover" />
          </div>
          <div className="absolute -bottom-3 -right-3 bg-[#1a1410] text-[#c9a876] w-28 h-28 rounded-full flex flex-col items-center justify-center text-center p-2">
            <span className="font-serif text-3xl leading-none">9</span>
            <span className="text-[10px] tracking-[0.2em] uppercase mt-1">Year Old<br />Founder</span>
          </div>
        </div>

        <div className="lg:col-span-3">
          <p className="text-xs tracking-[0.3em] uppercase text-[#8b6b4f] mb-4">Meet the Founder</p>
          <h2 className="font-serif text-4xl md:text-5xl text-[#1a1410] mb-6 leading-tight">Hi, I&rsquo;m <span className="italic">Luca</span></h2>
          <p className="text-[#3d3128] leading-relaxed mb-6">
            I&rsquo;m a nine-year-old entrepreneur, and the founder of Essential Gemstones. I love bringing the magic of natural stones to life by creating special, meaningful pieces for you.
          </p>
          <div className="space-y-5">
            <div className="flex gap-4">
              <Sparkles className="w-5 h-5 text-[#6b4f3a] mt-1 shrink-0" />
              <div>
                <h4 className="font-serif text-lg text-[#1a1410] mb-1">Why I Love Gemstones</h4>
                <p className="text-sm text-[#5a4a3d] leading-relaxed">For me, gemstones and crystals are simply amazing. Each one has its own vibrant color, unique energy, and a fascinating story.</p>
              </div>
            </div>
            <div className="flex gap-4">
              <Lightbulb className="w-5 h-5 text-[#6b4f3a] mt-1 shrink-0" />
              <div>
                <h4 className="font-serif text-lg text-[#1a1410] mb-1">How It Started</h4>
                <p className="text-sm text-[#5a4a3d] leading-relaxed">Gemstones always felt magical to me, and I wanted to share that feeling with everyone. I hand-pick every stone with purpose and design each piece with care.</p>
              </div>
            </div>
            <div className="flex gap-4">
              <Heart className="w-5 h-5 text-[#6b4f3a] mt-1 shrink-0" />
              <div>
                <h4 className="font-serif text-lg text-[#1a1410] mb-1">My Promise to You</h4>
                <p className="text-sm text-[#5a4a3d] leading-relaxed">Even though I&rsquo;m young, I take my business very seriously. Essential Gemstones is my dream, and I&rsquo;m incredibly proud of every bracelet I make.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
