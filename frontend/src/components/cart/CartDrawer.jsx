import React from 'react';
import { X, Trash2, Plus, Minus, ShoppingBag, ExternalLink } from 'lucide-react';
import { useCart, formatCents } from '../../context/CartContext';
import { resolveMediaUrl } from '../../lib/api';

export default function CartDrawer() {
  const { items, open, setOpen, removeItem, setQty, subtotalCents, count, clear } = useCart();
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[70]">
      <div className="absolute inset-0 bg-[#1a1410]/50 backdrop-blur-sm" onClick={() => setOpen(false)} />
      <aside className="absolute top-0 right-0 h-full w-full sm:w-[420px] bg-[#faf6f0] shadow-2xl flex flex-col animate-in slide-in-from-right">
        {/* Header */}
        <div className="px-5 py-4 border-b border-[#e8dfd1] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShoppingBag className="w-4 h-4 text-[#6b4f3a]" />
            <h3 className="font-serif text-lg text-[#1a1410]">Your cart</h3>
            <span className="text-xs text-[#8b6b4f]">({count} item{count === 1 ? '' : 's'})</span>
          </div>
          <button onClick={() => setOpen(false)} className="w-9 h-9 rounded-full hover:bg-[#f3ece0] flex items-center justify-center text-[#5a4a3d]" aria-label="Close cart"><X className="w-4 h-4" /></button>
        </div>

        {/* Items */}
        <div className="flex-1 overflow-y-auto">
          {items.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center px-6 py-12 text-center">
              <ShoppingBag className="w-10 h-10 text-[#c9a876] mb-4" />
              <p className="font-serif text-lg text-[#1a1410] mb-2">Your cart is empty</p>
              <p className="text-sm text-[#5a4a3d] mb-6">Add a bracelet to get started.</p>
              <button onClick={() => setOpen(false)} className="px-6 py-2.5 border border-[#3d3128] text-[#3d3128] rounded-full text-sm hover:bg-[#3d3128] hover:text-[#faf6f0] transition-colors">Continue browsing</button>
            </div>
          ) : (
            <div className="divide-y divide-[#e8dfd1]">
              {items.map((it) => (
                <div key={it.id} className="p-4 flex gap-3">
                  <div className="w-20 h-20 rounded-xl overflow-hidden bg-[#e8dfd1] shrink-0">
                    {it.image && <img src={resolveMediaUrl(it.image)} alt={it.name} className="w-full h-full object-cover" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <h4 className="font-serif text-sm text-[#1a1410] leading-snug">{it.name}</h4>
                      <button onClick={() => removeItem(it.id)} className="text-[#8b6b4f] hover:text-red-700 shrink-0" aria-label="Remove"><Trash2 className="w-4 h-4" /></button>
                    </div>
                    <p className="text-sm text-[#6b4f3a] font-serif mt-1">{it.price}</p>
                    <div className="mt-2 flex items-center justify-between">
                      <div className="inline-flex items-center border border-[#e8dfd1] rounded-full overflow-hidden bg-white">
                        <button onClick={() => setQty(it.id, it.quantity - 1)} disabled={it.quantity <= 1} className="w-7 h-7 flex items-center justify-center text-[#3d3128] hover:bg-[#f3ece0] disabled:opacity-40" aria-label="Decrease"><Minus className="w-3 h-3" /></button>
                        <span className="w-8 text-center text-sm text-[#1a1410]">{it.quantity}</span>
                        <button onClick={() => setQty(it.id, it.quantity + 1)} className="w-7 h-7 flex items-center justify-center text-[#3d3128] hover:bg-[#f3ece0]" aria-label="Increase"><Plus className="w-3 h-3" /></button>
                      </div>
                      <span className="text-sm text-[#1a1410]">{formatCents(it.priceCents * it.quantity)}</span>
                    </div>
                    {it.buyUrl && (
                      <a href={it.buyUrl} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full bg-[#1a1410] text-[#faf6f0] hover:bg-[#6b4f3a] transition-colors">
                        Pay for this item <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        {items.length > 0 && (
          <div className="border-t border-[#e8dfd1] p-5 bg-white">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm text-[#5a4a3d]">Subtotal</span>
              <span className="font-serif text-lg text-[#1a1410]">{formatCents(subtotalCents)}</span>
            </div>
            <p className="text-xs text-[#8b6b4f] mb-4">Each item checks out on its own secure page. Click &ldquo;Pay for this item&rdquo; on each bracelet above to complete your order.</p>
            <button onClick={clear} className="w-full py-2 text-xs text-[#8b6b4f] hover:text-[#3d3128] underline underline-offset-4">Clear cart</button>
          </div>
        )}
      </aside>
    </div>
  );
}
