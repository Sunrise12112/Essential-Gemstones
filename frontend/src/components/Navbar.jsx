import React, { useState, useEffect } from 'react';
import { Menu, X, Gem } from 'lucide-react';
import { useSite } from '../context/SiteContext';

export default function Navbar() {
  const { site } = useSite();
  const nav = site.navbar || {};
  const links = nav.links || [];
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <header className={`fixed top-0 left-0 right-0 z-50 transition-colors duration-500 ${scrolled ? 'bg-[#faf6f0]/95 backdrop-blur-md border-b border-[#e8dfd1]' : 'bg-transparent'}`}>
      <div className="max-w-7xl mx-auto px-6 md:px-10 py-5 flex items-center justify-between">
        <a href="#top" className="flex items-center gap-2 group">
          <Gem className="w-5 h-5 text-[#6b4f3a]" />
          <span className="font-serif text-xl tracking-wide text-[#2c2420]">{nav.brand || 'Essential Gemstones'}</span>
        </a>

        <nav className="hidden md:flex items-center gap-9">
          {links.map((l, i) => (
            <a key={i} href={l.href} className="text-sm tracking-wide text-[#3d3128] hover:text-[#6b4f3a] transition-colors relative group">
              {l.label}
              <span className="absolute -bottom-1 left-0 h-px w-0 bg-[#6b4f3a] transition-all duration-300 group-hover:w-full"></span>
            </a>
          ))}
          {nav.ctaLabel && (
            <a href={nav.ctaHref || '#shop'} className="px-5 py-2.5 text-sm bg-[#2c2420] text-[#faf6f0] rounded-full hover:bg-[#6b4f3a] transition-colors">
              {nav.ctaLabel}
            </a>
          )}
        </nav>

        <button className="md:hidden text-[#2c2420]" onClick={() => setOpen(!open)} aria-label="menu">
          {open ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      {open && (
        <div className="md:hidden bg-[#faf6f0] border-t border-[#e8dfd1] px-6 py-6 flex flex-col gap-4">
          {links.map((l, i) => (
            <a key={i} href={l.href} onClick={() => setOpen(false)} className="text-base text-[#3d3128] hover:text-[#6b4f3a]">{l.label}</a>
          ))}
          {nav.ctaLabel && <a href={nav.ctaHref || '#shop'} onClick={() => setOpen(false)} className="mt-2 inline-block w-fit px-5 py-2.5 text-sm bg-[#2c2420] text-[#faf6f0] rounded-full">{nav.ctaLabel}</a>}
        </div>
      )}
    </header>
  );
}
