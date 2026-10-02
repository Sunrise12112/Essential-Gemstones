import React from 'react';

// Renders an AI/admin-created section so it looks like a native site section.
// bg: 'light' (#faf6f0) | 'stone' (#f1e7d6) | 'dark' (#1a1410)
const BG = {
  light: { section: 'bg-[#faf6f0]', heading: 'text-[#1a1410]', text: 'text-[#5a4a3d]', kicker: 'text-[#6b4f3a]', caption: 'text-[#8b6b4f]', quote: 'bg-white border-[#e8dfd1] text-[#3d3128]' },
  stone: { section: 'bg-[#f1e7d6]', heading: 'text-[#1a1410]', text: 'text-[#5a4a3d]', kicker: 'text-[#6b4f3a]', caption: 'text-[#8b6b4f]', quote: 'bg-[#faf6f0] border-[#e2d5c0] text-[#3d3128]' },
  dark: { section: 'bg-[#1a1410] text-[#faf6f0]', heading: 'text-[#faf6f0]', text: 'text-[#d4c5af]', kicker: 'text-[#c9a876]', caption: 'text-[#bfae95]', quote: 'bg-[#241b15] border-[#3d2f24] text-[#e9d9bf]' },
};

export default function CustomSection({ section }) {
  if (!section || !Array.isArray(section.blocks)) return null;
  const theme = BG[section.bg] || BG.light;
  const blocks = section.blocks;

  return (
    <section id={section.id} data-testid={`custom-section-${section.id}`} className={`py-24 md:py-32 ${theme.section}`}>
      <div className="max-w-7xl mx-auto px-6 md:px-10">
        <div className="max-w-3xl mx-auto text-center flex flex-col items-center gap-6">
          {blocks.map((b, i) => {
            if (!b || typeof b !== 'object') return null;
            const key = `${section.id}-${i}`;
            const alignSelf = b.align === 'left' ? 'self-start text-left' : 'text-center';
            switch (b.type) {
              case 'kicker':
                return <p key={key} className={`text-xs tracking-[0.3em] uppercase ${theme.kicker}`}>{b.text}</p>;
              case 'heading':
                return <h2 key={key} className={`font-serif text-4xl md:text-5xl leading-tight ${theme.heading} ${alignSelf}`}>{b.text}</h2>;
              case 'paragraph':
                return <p key={key} className={`text-base md:text-lg leading-relaxed ${theme.text} ${alignSelf}`}>{b.text}</p>;
              case 'quote':
                return (
                  <blockquote key={key} className={`w-full rounded-3xl border p-7 md:p-8 shadow-sm ${theme.quote}`}>
                    <p className="font-serif text-xl md:text-2xl leading-relaxed">&ldquo;{b.text}&rdquo;</p>
                    {b.author && <footer className={`mt-4 text-xs tracking-[0.2em] uppercase ${theme.kicker}`}>{b.author}</footer>}
                  </blockquote>
                );
              case 'image':
                return (
                  <figure key={key} className="w-full my-2">
                    <img src={b.src} alt={b.alt || ''} loading="lazy" className="w-full rounded-3xl shadow-lg object-cover" />
                    {b.caption && <figcaption className={`mt-3 text-sm ${theme.caption}`}>{b.caption}</figcaption>}
                  </figure>
                );
              case 'button':
                return (
                  <div key={key}>
                    <a
                      href={b.href || '#'}
                      target={(b.href || '').startsWith('http') ? '_blank' : undefined}
                      rel="noreferrer"
                      data-testid={`custom-section-btn-${section.id}-${i}`}
                      className={`inline-block px-8 py-3.5 rounded-full text-sm tracking-wider uppercase transition-colors ${
                        b.style === 'outline'
                          ? 'border border-current hover:bg-[#1a1410] hover:text-[#faf6f0]'
                          : 'bg-[#1a1410] text-[#faf6f0] hover:bg-[#6b4f3a]'
                      }`}
                    >
                      {b.label || 'Learn more'}
                    </a>
                  </div>
                );
              case 'divider':
                return <hr key={key} className="w-16 border-0 h-px bg-current opacity-20" />;
              case 'embed':
                return <div key={key} className="w-full overflow-hidden rounded-2xl" dangerouslySetInnerHTML={{ __html: b.html || '' }} />;
              default:
                return null;
            }
          })}
        </div>
      </div>
    </section>
  );
}
