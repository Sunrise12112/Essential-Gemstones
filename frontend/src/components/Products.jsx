import React, { useState } from 'react';
import { ArrowUpRight, Heart, Eye } from 'lucide-react';
import { useSite } from '../context/SiteContext';
import { useAuth } from '../context/AuthContext';
import { resolveMediaUrl } from '../lib/api';
import { useToast } from '../hooks/use-toast';
import ProductModal from './ProductModal';

export default function Products() {
  const { site } = useSite();
  const { user, toggleFavorite } = useAuth();
  const { toast } = useToast();
  const p = site.products || {};
  const items = p.items || [];
  const favorites = user?.favorites || [];
  const [openItem, setOpenItem] = useState(null);

  const onHeart = async (e, item) => {
    e.stopPropagation();
    const res = await toggleFavorite(item.id);
    if (res?.needsAuth) {
      toast({ title: 'Create a free account', description: 'Sign up to save your favorite pieces.' });
    } else if (res?.favorited) {
      toast({ title: 'Saved to favorites', description: item.name });
    }
  };

  const onBuyClick = (e) => {
    // Don't open the modal if the user clicks the Buy button directly on the card
    e.stopPropagation();
  };

  return (
    <section id="shop" className="py-24 md:py-32 bg-[#f3ece0]">
      <div className="max-w-7xl mx-auto px-6 md:px-10">
        <div className="text-center mb-16">
          {p.kicker && <p className="text-xs tracking-[0.3em] uppercase text-[#8b6b4f] mb-4">{p.kicker}</p>}
          {p.title && <h2 className="font-serif text-4xl md:text-5xl text-[#1a1410] mb-4">{p.title}</h2>}
          {p.subtitle && <p className="text-[#5a4a3d] max-w-2xl mx-auto">{p.subtitle}</p>}
        </div>

        <div className="grid md:grid-cols-2 gap-8 md:gap-12">
          {items.map((it, i) => {
            const isFav = favorites.includes(it.id);
            return (
              <article
                key={it.id || i}
                onClick={() => setOpenItem(it)}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setOpenItem(it); } }}
                role="button"
                tabIndex={0}
                data-testid={`product-card-${it.id || i}`}
                className="group bg-[#faf6f0] rounded-3xl overflow-hidden border border-[#e8dfd1] hover:shadow-2xl transition-all duration-500 cursor-pointer focus:outline-none focus:ring-2 focus:ring-[#6b4f3a] focus:ring-offset-2 focus:ring-offset-[#f3ece0]"
              >
                <div className="relative aspect-[4/3] overflow-hidden bg-[#e8dfd1]">
                  {it.image && <img src={resolveMediaUrl(it.image)} alt={it.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700" />}
                  {it.badge && (
                    <div className="absolute top-4 left-4 bg-[#faf6f0]/90 backdrop-blur px-3 py-1 rounded-full">
                      <span className="text-[10px] tracking-[0.2em] uppercase text-[#3d3128]">{it.badge}</span>
                    </div>
                  )}
                  <button
                    onClick={(e) => onHeart(e, it)}
                    aria-label={isFav ? 'Remove from favorites' : 'Save to favorites'}
                    data-testid={`product-card-favorite-${it.id || i}`}
                    className="absolute top-4 right-4 w-11 h-11 rounded-full bg-[#faf6f0]/90 backdrop-blur hover:bg-[#faf6f0] flex items-center justify-center transition-transform hover:scale-110 shadow-md"
                  >
                    <Heart className={`w-5 h-5 ${isFav ? 'fill-[#c9483d] text-[#c9483d]' : 'text-[#3d3128]'}`} />
                  </button>
                  {/* Quick-view hint on hover */}
                  <div className="absolute inset-0 bg-[#1a1410]/0 group-hover:bg-[#1a1410]/10 transition-colors flex items-end justify-center pb-4 pointer-events-none">
                    <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#faf6f0]/95 text-[#1a1410] text-[11px] tracking-wider uppercase opacity-0 group-hover:opacity-100 transition-opacity">
                      <Eye className="w-3 h-3" /> View details
                    </span>
                  </div>
                </div>
                <div className="p-7 md:p-9">
                  <h3 className="font-serif text-2xl md:text-3xl text-[#1a1410] mb-3">{it.name}</h3>
                  {it.description && <p className="text-[#5a4a3d] mb-6 leading-relaxed">{it.description}</p>}
                  <div className="flex items-center justify-between">
                    {it.price && <span className="font-serif text-xl text-[#6b4f3a]">{it.price}</span>}
                    {it.buyUrl ? (
                      <a
                        href={it.buyUrl}
                        target="_blank"
                        rel="noreferrer"
                        onClick={onBuyClick}
                        className="inline-flex items-center gap-2 px-5 py-3 bg-[#1a1410] text-[#faf6f0] rounded-full text-sm hover:bg-[#6b4f3a] transition-colors"
                      >
                        Buy Now <ArrowUpRight className="w-4 h-4" />
                      </a>
                    ) : (
                      <span className="text-xs tracking-wider uppercase text-[#8b6b4f]">Tap for details</span>
                    )}
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      </div>

      <ProductModal
        product={openItem}
        open={!!openItem}
        onClose={() => setOpenItem(null)}
      />
    </section>
  );
}
