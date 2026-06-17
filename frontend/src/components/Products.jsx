import React from 'react';
import { products } from '../mock';
import { ArrowUpRight } from 'lucide-react';

export default function Products() {
  return (
    <section id="shop" className="py-24 md:py-32 bg-[#f3ece0]">
      <div className="max-w-7xl mx-auto px-6 md:px-10">
        <div className="text-center mb-16">
          <p className="text-xs tracking-[0.3em] uppercase text-[#8b6b4f] mb-4">Shop Our Latest Creations</p>
          <h2 className="font-serif text-4xl md:text-5xl text-[#1a1410] mb-4">The Collection</h2>
          <p className="text-[#5a4a3d] max-w-2xl mx-auto">Discover our unique selection of handcrafted lava stone bracelets. Each piece is designed to bring natural beauty and strength to your daily life.</p>
        </div>

        <div className="grid md:grid-cols-2 gap-8 md:gap-12">
          {products.map(p => (
            <article key={p.id} className="group bg-[#faf6f0] rounded-3xl overflow-hidden border border-[#e8dfd1] hover:shadow-2xl transition-all duration-500">
              <div className="relative aspect-[4/3] overflow-hidden bg-[#e8dfd1]">
                <img src={p.image} alt={p.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700" />
                <div className="absolute top-4 left-4 bg-[#faf6f0]/90 backdrop-blur px-3 py-1 rounded-full">
                  <span className="text-[10px] tracking-[0.2em] uppercase text-[#3d3128]">New</span>
                </div>
              </div>
              <div className="p-7 md:p-9">
                <h3 className="font-serif text-2xl md:text-3xl text-[#1a1410] mb-3">{p.name}</h3>
                <p className="text-[#5a4a3d] mb-6 leading-relaxed">{p.description}</p>
                <div className="flex items-center justify-between">
                  <span className="font-serif text-xl text-[#6b4f3a]">{p.price}</span>
                  <a href={p.buyUrl} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 px-5 py-3 bg-[#1a1410] text-[#faf6f0] rounded-full text-sm hover:bg-[#6b4f3a] transition-colors">
                    Buy Now
                    <ArrowUpRight className="w-4 h-4" />
                  </a>
                </div>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
