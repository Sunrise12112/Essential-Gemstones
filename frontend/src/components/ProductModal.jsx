import React, { useEffect, useState, useCallback, useRef } from 'react';
import { X, Heart, ArrowUpRight, Bell, BellRing, ShieldCheck, Sparkles, Truck } from 'lucide-react';
import api, { resolveMediaUrl } from '../lib/api';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../hooks/use-toast';

export default function ProductModal({ product, open, onClose }) {
  const { user, toggleFavorite } = useAuth();
  const { toast } = useToast();
  const [imgIndex, setImgIndex] = useState(0);
  const [waitlistJoined, setWaitlistJoined] = useState(false);
  const [guestEmail, setGuestEmail] = useState('');
  const [waiting, setWaiting] = useState(false);
  const dialogRef = useRef(null);

  const gallery = React.useMemo(() => {
    if (!product) return [];
    const extra = Array.isArray(product.gallery) ? product.gallery : [];
    const primary = product.image ? [product.image] : [];
    return [...primary, ...extra].filter(Boolean);
  }, [product]);

  const isFav = user?.favorites?.includes(product?.id);

  useEffect(() => {
    if (open) {
      setImgIndex(0);
      setWaitlistJoined(false);
      setGuestEmail('');
    }
  }, [open, product?.id]);

  // Lock body scroll while open
  useEffect(() => {
    if (!open) return undefined;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = prev; };
  }, [open]);

  // ESC to close, arrow keys for gallery
  const handleKey = useCallback((e) => {
    if (!open) return;
    if (e.key === 'Escape') onClose();
    if (e.key === 'ArrowRight' && gallery.length > 1) setImgIndex((i) => (i + 1) % gallery.length);
    if (e.key === 'ArrowLeft' && gallery.length > 1) setImgIndex((i) => (i - 1 + gallery.length) % gallery.length);
  }, [open, onClose, gallery.length]);

  useEffect(() => {
    if (!open) return undefined;
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [open, handleKey]);

  if (!open || !product) return null;

  const onHeart = async () => {
    const res = await toggleFavorite(product.id);
    if (res?.needsAuth) {
      toast({ title: 'Create a free account', description: 'Sign up to save your favorite pieces.' });
    } else if (res?.favorited) {
      toast({ title: 'Saved to favorites', description: product.name });
    } else if (res?.favorited === false) {
      toast({ title: 'Removed from favorites', description: product.name });
    }
  };

  const joinWaitlist = async () => {
    setWaiting(true);
    try {
      const body = user ? {} : { email: guestEmail.trim() };
      if (!user && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(body.email || '')) {
        toast({ title: 'Email needed', description: 'Enter a valid email so we can let you know.', variant: 'destructive' });
        return;
      }
      const { data } = await api.post(`/products/${product.id}/waitlist`, body);
      setWaitlistJoined(true);
      toast({
        title: data.already ? "You're already on the list" : "On the list",
        description: `We'll email ${data.email} when this piece is available.`,
      });
    } catch (e) {
      toast({ title: 'Couldn\u2019t join the list', description: e?.response?.data?.detail || e.message, variant: 'destructive' });
    } finally {
      setWaiting(false);
    }
  };

  const backdropClick = (e) => {
    if (e.target === dialogRef.current) onClose();
  };

  const primaryImage = gallery[imgIndex] || product.image;

  return (
    <div
      ref={dialogRef}
      onClick={backdropClick}
      role="dialog"
      aria-modal="true"
      aria-labelledby={`product-modal-title-${product.id}`}
      data-testid="product-modal"
      className="fixed inset-0 z-[100] bg-[#1a1410]/70 backdrop-blur-sm flex items-start md:items-center justify-center p-3 md:p-8 overflow-y-auto"
    >
      <div className="relative w-full max-w-6xl bg-[#faf6f0] rounded-3xl border border-[#e8dfd1] shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Close */}
        <button
          onClick={onClose}
          aria-label="Close product"
          data-testid="product-modal-close"
          className="absolute top-4 right-4 z-10 w-11 h-11 rounded-full bg-[#faf6f0]/95 backdrop-blur border border-[#e8dfd1] hover:bg-white flex items-center justify-center transition-colors"
        >
          <X className="w-5 h-5 text-[#3d3128]" />
        </button>

        <div className="grid md:grid-cols-2">
          {/* Gallery */}
          <div className="bg-[#e8dfd1] relative aspect-[4/5] md:aspect-auto md:min-h-[560px]">
            {primaryImage && (
              <img
                src={resolveMediaUrl(primaryImage)}
                alt={product.name}
                className="absolute inset-0 w-full h-full object-cover"
                data-testid="product-modal-image"
              />
            )}
            {product.badge && (
              <div className="absolute top-5 left-5 bg-[#faf6f0]/90 backdrop-blur px-3 py-1 rounded-full">
                <span className="text-[10px] tracking-[0.2em] uppercase text-[#3d3128]">{product.badge}</span>
              </div>
            )}
            {gallery.length > 1 && (
              <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-1.5 bg-[#faf6f0]/80 backdrop-blur px-3 py-2 rounded-full">
                {gallery.map((_, i) => (
                  <button
                    key={i}
                    onClick={() => setImgIndex(i)}
                    aria-label={`Show image ${i + 1}`}
                    data-testid={`product-modal-dot-${i}`}
                    className={`w-2 h-2 rounded-full transition-all ${i === imgIndex ? 'bg-[#1a1410] w-6' : 'bg-[#8b6b4f]/50 hover:bg-[#8b6b4f]'}`}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Details */}
          <div className="p-7 md:p-10 lg:p-12 overflow-y-auto max-h-[85vh]">
            <div className="flex items-start justify-between gap-4 mb-3">
              <div>
                {product.kicker && <p className="text-xs tracking-[0.3em] uppercase text-[#8b6b4f] mb-2">{product.kicker}</p>}
                <h2 id={`product-modal-title-${product.id}`} className="font-serif text-3xl md:text-4xl lg:text-5xl text-[#1a1410] leading-tight">
                  {product.name}
                </h2>
              </div>
              <button
                onClick={onHeart}
                aria-label={isFav ? 'Remove from favorites' : 'Save to favorites'}
                data-testid="product-modal-favorite"
                className="w-12 h-12 shrink-0 rounded-full bg-white border border-[#e8dfd1] hover:bg-[#faf6f0] flex items-center justify-center transition-transform hover:scale-105"
              >
                <Heart className={`w-5 h-5 ${isFav ? 'fill-[#c9483d] text-[#c9483d]' : 'text-[#3d3128]'}`} />
              </button>
            </div>

            {product.price && (
              <div className="font-serif text-2xl text-[#6b4f3a] mb-6" data-testid="product-modal-price">{product.price}</div>
            )}

            {product.description && (
              <p className="text-[#3d3128] leading-relaxed mb-6" data-testid="product-modal-description">
                {product.description}
              </p>
            )}

            {product.longDescription && (
              <div className="prose prose-sm max-w-none text-[#3d3128] leading-relaxed mb-6 whitespace-pre-wrap" data-testid="product-modal-longdesc">
                {product.longDescription}
              </div>
            )}

            {/* Feature bullets */}
            {(product.details || product.features || []).length > 0 && (
              <div className="mb-6">
                <div className="text-xs tracking-[0.2em] uppercase text-[#8b6b4f] mb-3">Details</div>
                <ul className="space-y-2 text-sm text-[#3d3128]">
                  {(product.details || product.features || []).map((d, i) => (
                    <li key={i} className="flex items-start gap-2" data-testid={`product-modal-detail-${i}`}>
                      <span className="w-1 h-1 rounded-full bg-[#8b6b4f] mt-2 shrink-0" />
                      <span>{d}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Trust row */}
            <div className="grid grid-cols-3 gap-2 mb-8 text-[10px] tracking-wider uppercase text-[#8b6b4f]">
              <div className="flex flex-col items-center gap-1 py-3 border border-[#e8dfd1] rounded-xl bg-white">
                <Sparkles className="w-4 h-4 text-[#6b4f3a]" />
                <span>Handmade</span>
              </div>
              <div className="flex flex-col items-center gap-1 py-3 border border-[#e8dfd1] rounded-xl bg-white">
                <ShieldCheck className="w-4 h-4 text-[#6b4f3a]" />
                <span>Real stones</span>
              </div>
              <div className="flex flex-col items-center gap-1 py-3 border border-[#e8dfd1] rounded-xl bg-white">
                <Truck className="w-4 h-4 text-[#6b4f3a]" />
                <span>Ships in 3–5 days</span>
              </div>
            </div>

            {/* CTA row */}
            <div className="space-y-3">
              {product.buyUrl ? (
                <a
                  href={product.buyUrl}
                  target="_blank"
                  rel="noreferrer"
                  data-testid="product-modal-buy"
                  className="w-full inline-flex items-center justify-center gap-2 px-6 py-4 bg-[#1a1410] text-[#faf6f0] rounded-full text-sm tracking-wider uppercase hover:bg-[#6b4f3a] transition-colors"
                >
                  Buy now <ArrowUpRight className="w-4 h-4" />
                </a>
              ) : (
                <div className="w-full text-center px-6 py-4 border border-[#e8dfd1] rounded-full text-sm uppercase tracking-wider text-[#8b6b4f] bg-white">
                  Currently unavailable
                </div>
              )}

              {/* Waitlist */}
              {!waitlistJoined ? (
                <div className="border border-[#e8dfd1] rounded-2xl p-4 bg-white">
                  <div className="flex items-center gap-2 mb-1 text-[#6b4f3a]">
                    <Bell className="w-4 h-4" />
                    <span className="text-xs tracking-[0.2em] uppercase">Notify me</span>
                  </div>
                  <p className="text-xs text-[#5a4a3d] mb-3">
                    Get an email when this piece is back in stock or ready to ship. Also lets Luca know it's wanted.
                  </p>
                  {!user && (
                    <input
                      type="email"
                      value={guestEmail}
                      onChange={(e) => setGuestEmail(e.target.value)}
                      placeholder="you@example.com"
                      data-testid="product-modal-waitlist-email"
                      className="w-full mb-2 px-4 py-2.5 text-sm border border-[#e8dfd1] rounded-full bg-[#faf6f0] focus:outline-none focus:border-[#6b4f3a]"
                    />
                  )}
                  <button
                    onClick={joinWaitlist}
                    disabled={waiting || (!user && !guestEmail.trim())}
                    data-testid="product-modal-waitlist-submit"
                    className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 border border-[#1a1410] text-[#1a1410] rounded-full text-sm hover:bg-[#1a1410] hover:text-[#faf6f0] transition-colors disabled:opacity-50"
                  >
                    <BellRing className="w-4 h-4" />
                    {waiting ? 'Adding\u2026' : (user ? 'Add me to the list' : 'Join the waitlist')}
                  </button>
                </div>
              ) : (
                <div className="border border-green-200 bg-green-50 rounded-2xl p-4 flex items-center gap-2" data-testid="product-modal-waitlist-success">
                  <BellRing className="w-5 h-5 text-green-700" />
                  <div>
                    <div className="text-sm text-green-900 font-medium">You're on the list.</div>
                    <div className="text-xs text-green-800">We'll email you when it's available.</div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
