import React from 'react';

// Renders an AI/admin-created section made of simple blocks.
// bg: 'light' (#faf6f0) | 'stone' (#f1e7d6) | 'dark' (#1a1410)
const BG = {
  light: { section: 'bg-[#faf6f0]', heading: 'text-[#1a1410]', text: 'text-[#5a4a3d]', kicker: 'text-[#6b4f3a]', caption: 'text-[#8b6b4f]' },
  stone: { section: 'bg-[#f1e7d6]', heading: 'text-[#1a1410]', text: 'text-[#5a4a3d]', kicker: 'text-[#6b4f3a]', caption: 'text-[#8b6b4f]' },
  dark: { section: 'bg-[#1a1410] text-[#faf6f0]', heading: 'text-[#faf6f0]', text: 'text-[#d4c5af]', kicker: 'text-[#c9a876]', caption: 'text-[#bfae95]' },
};

export default function CustomSection({ section }) {
  if (!section || !Array.isArray(section.blocks)) return null;
  const theme = BG[section.bg] || BG.light;

  return (
    <section id={section.id} data-testid={`custom-section-${section.id}`} className={`py-20 md:py-28 ${theme.section}`}>
      <div className="max-w-4xl mx-auto px-6 md:px-10 space-y-6">
        {section.blocks.map((b, i) => {
          if (!b || typeof b !== 'object') return null;
          const key = `${section.id}-${i}`;
          switch (b.type) {
            case 'kicker':
              return <p key={key} className={`text-xs tracking-[0.3em] uppercase ${theme.kicker}`}>{b.text}</p>;
            case 'heading':
              return <h2 key={key} className={`font-serif text-4xl md:text-5xl leading-tight ${theme.heading} ${b.align === 'center' ? 'text-center' : ''}`}>{b.text}</h2>;
            case 'paragraph':
              return <p key={key} className={`text-base md:text-lg leading-relaxed ${theme.text} ${b.align === 'center' ? 'text-center' : ''}`}>{b.text}</p>;
            case 'image':
              return (
                <figure key={key} className="my-2">
                  <img src={b.src} alt={b.alt || ''} loading="lazy" className="w-full rounded-3xl shadow-lg object-cover" />
                  {b.caption && <figcaption className={`mt-3 text-sm text-center ${theme.caption}`}>{b.caption}</figcaption>}
                </figure>
              );
            case 'button':
              return (
                <div key={key} className={b.align === 'center' ? 'text-center' : ''}>
                  <a
                    href={b.href || '#'}
                    target={(b.href || '').startsWith('http') ? '_blank' : undefined}
                    rel="noreferrer"
                    data-testid={`custom-section-btn-${section.id}-${i}`}
                    className={`inline-block px-7 py-3 rounded-full text-sm tracking-wider uppercase transition-colors ${
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
              return <hr key={key} className="border-0 h-px bg-current opacity-15 my-4" />;
            case 'embed':
              return <div key={key} className="w-full overflow-hidden rounded-2xl" dangerouslySetInnerHTML={{ __html: b.html || '' }} />;
            default:
              return null;
          }
        })}
      </div>
    </section>
  );
}
