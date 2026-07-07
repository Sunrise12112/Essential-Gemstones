import React from 'react';
import { ArrowUpRight, Heart } from 'lucide-react';
import { useSite } from '../context/SiteContext';
import { useAuth } from '../context/AuthContext';
import { resolveMediaUrl } from '../lib/api';
import { useToast } from '../hooks/use-toast';

export default function Products() {
  const { site } = useSite();
  const { user, toggleFavorite } = useAuth();
  const { toast } = useToast();
  const p = site.products || {};
  const items = p.items || [];
  const favorites = user?.favorites || [];

  const onHeart = async (item) => {
    const res = await toggleFavorite(item.id);
    if (res?.needsAuth) {
      toast({ title: 'Create a free account', description: 'Sign up to save your favorite pieces.' });
    } else if (res?.favorited) {
      toast({ title: 'Saved to favorites', description: item.name });
    }
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
              <article key={it.id || i} className="group bg-[#faf6f0] rounded-3xl overflow-hidden border border-[#e8dfd1] hover:shadow-2xl transition-all duration-500">
                <div className="relative aspect-[4/3] overflow-hidden bg-[#e8dfd1]">
                  {it.image && <img src={resolveMediaUrl(it.image)} alt={it.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700" />}
                  {it.badge && (
                    <div className="absolute top-4 left-4 bg-[#faf6f0]/90 backdrop-blur px-3 py-1 rounded-full">
                      <span className="text-[10px] tracking-[0.2em] uppercase text-[#3d3128]">{it.badge}</span>
                    </div>
                  )}
                  <button
                    onClick={() => onHeart(it)}
                    aria-label={isFav ? 'Remove from favorites' : 'Save to favorites'}
                    className="absolute top-4 right-4 w-11 h-11 rounded-full bg-[#faf6f0]/90 backdrop-blur hover:bg-[#faf6f0] flex items-center justify-center transition-transform hover:scale-110 shadow-md"
                  >
                    <Heart className={`w-5 h-5 ${isFav ? 'fill-[#c9483d] text-[#c9483d]' : 'text-[#3d3128]'}`} />
                  </button>
                </div>
                <div className="p-7 md:p-9">
                  <h3 className="font-serif text-2xl md:text-3xl text-[#1a1410] mb-3">{it.name}</h3>
                  {it.description && <p className="text-[#5a4a3d] mb-6 leading-relaxed">{it.description}</p>}
                  <div className="flex items-center justify-between">
                    {it.price && <span className="font-serif text-xl text-[#6b4f3a]">{it.price}</span>}
                    {it.buyUrl && (
                      <a href={it.buyUrl} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 px-5 py-3 bg-[#1a1410] text-[#faf6f0] rounded-full text-sm hover:bg-[#6b4f3a] transition-colors">
                        Buy Now <ArrowUpRight className="w-4 h-4" />
                      </a>
                    )}
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}
