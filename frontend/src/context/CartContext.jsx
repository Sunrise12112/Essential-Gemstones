import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

const CART_KEY = 'eg_cart_v1';
const CartContext = createContext({
  items: [],
  count: 0,
  subtotalCents: 0,
  open: false,
  setOpen: () => {},
  addItem: () => {},
  removeItem: () => {},
  setQty: () => {},
  clear: () => {},
});

function parsePrice(str) {
  if (typeof str !== 'string') return 0;
  const n = parseFloat(str.replace(/[^0-9.]/g, ''));
  if (Number.isNaN(n)) return 0;
  return Math.round(n * 100);
}

function load() {
  try { return JSON.parse(localStorage.getItem(CART_KEY)) || []; } catch (e) { return []; }
}
function save(items) {
  try { localStorage.setItem(CART_KEY, JSON.stringify(items)); } catch (e) { /* ignore */ }
}

export function CartProvider({ children }) {
  const [items, setItems] = useState(load);
  const [open, setOpen] = useState(false);

  useEffect(() => { save(items); }, [items]);

  const addItem = useCallback((product) => {
    if (!product?.id) return;
    setItems((prev) => {
      const idx = prev.findIndex((it) => it.id === product.id);
      if (idx >= 0) {
        const next = [...prev];
        next[idx] = { ...next[idx], quantity: next[idx].quantity + 1 };
        return next;
      }
      return [
        ...prev,
        {
          id: product.id,
          name: product.name,
          image: product.image,
          price: product.price,
          priceCents: parsePrice(product.price),
          buyUrl: product.buyUrl,
          quantity: 1,
        },
      ];
    });
    setOpen(true);
  }, []);

  const removeItem = useCallback((id) => {
    setItems((prev) => prev.filter((it) => it.id !== id));
  }, []);

  const setQty = useCallback((id, qty) => {
    setItems((prev) => prev.map((it) => (it.id === id ? { ...it, quantity: Math.max(1, qty) } : it)));
  }, []);

  const clear = useCallback(() => setItems([]), []);

  const count = items.reduce((n, it) => n + it.quantity, 0);
  const subtotalCents = items.reduce((n, it) => n + it.priceCents * it.quantity, 0);

  const value = useMemo(() => ({
    items, count, subtotalCents, open, setOpen, addItem, removeItem, setQty, clear,
  }), [items, count, subtotalCents, open, addItem, removeItem, setQty, clear]);

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart() {
  return useContext(CartContext);
}

export function formatCents(cents) {
  return `$${(cents / 100).toFixed(2)}`;
}
