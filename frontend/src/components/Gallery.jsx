import React from 'react';
import { galleryImages } from '../mock';

export default function Gallery() {
  return (
    <section className="py-24 md:py-32 bg-[#faf6f0]">
      <div className="max-w-7xl mx-auto px-6 md:px-10">
        <div className="text-center mb-14">
          <p className="text-xs tracking-[0.3em] uppercase text-[#8b6b4f] mb-4">Gallery</p>
          <h2 className="font-serif text-4xl md:text-5xl text-[#1a1410] leading-tight">A Closer Look at <span className="italic">Our Craft</span></h2>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-5">
          {galleryImages.map((img, i) => (
            <div key={i} className="group relative aspect-[3/4] overflow-hidden rounded-2xl">
              <img src={img} alt={`Craft ${i+1}`} className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700" />
              <div className="absolute inset-0 bg-[#1a1410]/0 group-hover:bg-[#1a1410]/15 transition-colors"></div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
