import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import api from '../lib/api';
import * as mock from '../mock';

const defaultSite = {
  navbar: {
    brand: 'Essential Gemstones',
    links: [
      { label: 'Shop', href: '#shop' },
      { label: 'Our Story', href: '#story' },
      { label: 'Chakra Guide', href: '#chakra' },
      { label: 'Founder', href: '#founder' },
      { label: 'FAQ', href: '#faq' },
      { label: 'Contact', href: '#contact' }
    ],
    ctaLabel: 'Shop Now',
    ctaHref: '#shop'
  },
  hero: {
    kicker: 'Handmade · Volcanic · Intentional',
    titleLine1: 'Essential',
    titleLine2: 'Gemstones',
    subtitle: 'Handmade lava stone bracelets inspired by nature and strength. Born from fire, shaped by hand — each piece carries a quiet story you can wear.',
    ctaPrimary: { label: 'Shop the Collection', href: '#shop' },
    ctaSecondary: { label: 'Our Story', href: '#story' },
    mediaType: 'image',
    mediaUrl: mock.heroImage,
    quoteText: 'What we wear can carry meaning.',
    quoteAuthor: '— LUCA, FOUNDER'
  },
  products: {
    kicker: 'Shop Our Latest Creations',
    title: 'The Collection',
    subtitle: 'Discover our unique selection of handcrafted lava stone bracelets.',
    items: mock.products.map((p) => ({ ...p, badge: 'New' }))
  },
  story: {
    kicker: 'Our Story',
    title: 'Born from the Earth, Made by Hand',
    image: mock.storyImage,
    badge: 'One bracelet at a time.',
    paragraphs: []
  },
  promise: { kicker: 'Our Promise', title: 'Why Choose Essential Gemstones?', body: '' },
  chakra: { kicker: 'Our Craft', title: 'Awaken Your Spirit: The 7 Chakra Bracelet', subtitle: '', footer: '', stones: mock.chakraStones },
  stats: { kicker: 'Best Sellers', title: 'Why Customers Love Us', items: mock.stats },
  lavaMeaning: { kicker: 'The Power Within', title: 'What Lava Stone Means', subtitle: '', items: mock.lavaMeanings },
  founder: { kicker: 'Meet the Founder', title: 'Hi, I’m Luca', image: mock.founderImage, ageBadge: '9', ageLabel: 'Year Old Founder', intro: '', blocks: [] },
  craft: { kicker: 'Craftsmanship', title: 'What Goes Into Every Bracelet', subtitle: '', image: mock.craftImage, steps: mock.craftSteps },
  faq: { kicker: 'FAQ', title: 'Frequently Asked Questions', subtitle: '', items: mock.faqs },
  gallery: { kicker: 'Gallery', title: 'A Closer Look at Our Craft', images: mock.galleryImages },
  vip: { kicker: 'Exclusive Access', title: 'Join our VIP Membership', subtitle: '', perks: [], ctaLabel: 'Join the VIP Club', ctaUrl: '#' },
  nanoAI: {
    kicker: 'A Little Something Extra',
    title: 'Meet Nano AI',
    subtitle: "You can also try out this business I've created called Nano AI — a personal AI chat companion that remembers helpful details, organizes your conversations, and gives you smart tools all in one simple place.",
    image: 'https://static.prod-images.emergentagent.com/jobs/2fde6317-a09a-43de-a20a-f1efe8d5d18d/images/a1df6793579e597138f81758ad1d4bf332dddc3df2909d9e59fdde83c7fffe1e.jpeg',
    features: [
      { title: 'Personalized memory', desc: 'Nano remembers your preferences and context across every conversation.' },
      { title: '17 AI models', desc: 'Switch between models from OpenAI, Anthropic, and Google — all in one place.' },
      { title: 'Create anything', desc: 'Generate documents, images, and even short videos from a simple message.' },
      { title: 'Free to start', desc: 'Start chatting in seconds — no credit card required for the Free plan.' },
    ],
    ctaLabel: 'Try Nano AI',
    ctaUrl: 'https://nano-ai.org',
    note: 'Another creation by Luca',
  },
  footer: { brand: 'Essential Gemstones', tagline: '', newsletterKicker: 'Stay Connected', newsletterTitle: 'Get the latest from the studio.', email: '', donateTitle: 'Support', donateText: '', donateUrl: '#', donateLabel: 'Donate Now', copyright: 'Handmade with intention.', quote: '', socials: { instagram: '#', facebook: '#' } },
  sectionOrder: ['hero', 'products', 'story', 'promise', 'chakra', 'stats', 'lavaMeaning', 'founder', 'craft', 'faq', 'gallery', 'vip', 'nanoAI'],
  sectionVisibility: { hero: true, products: true, story: true, promise: true, chakra: true, stats: true, lavaMeaning: true, founder: true, craft: true, faq: true, gallery: true, vip: true, nanoAI: true }
};

const SiteContext = createContext({ site: defaultSite, loading: true, refresh: () => {}, setSite: () => {} });

export function SiteProvider({ children }) {
  const [site, setSite] = useState(defaultSite);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      // Cache-bust to ensure fresh data across devices
      const { data } = await api.get(`/site?t=${Date.now()}`);
      setSite({ ...defaultSite, ...data });
    } catch (e) {
      // keep defaults (mock-backed)
      console.warn('Failed to load /site', e?.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  // Refresh content when tab/window regains focus so other devices see edits
  useEffect(() => {
    const onVis = () => { if (document.visibilityState === 'visible') refresh(); };
    const onFocus = () => refresh();
    document.addEventListener('visibilitychange', onVis);
    window.addEventListener('focus', onFocus);
    return () => {
      document.removeEventListener('visibilitychange', onVis);
      window.removeEventListener('focus', onFocus);
    };
  }, [refresh]);

  return (
    <SiteContext.Provider value={{ site, setSite, loading, refresh }}>
      {children}
    </SiteContext.Provider>
  );
}

export function useSite() {
  return useContext(SiteContext);
}
