import React from 'react';
import { useSite } from '../context/SiteContext';
import Navbar from '../components/Navbar';
import Hero from '../components/Hero';
import Products from '../components/Products';
import Story from '../components/Story';
import Promise from '../components/Promise';
import Chakra from '../components/Chakra';
import Stats from '../components/Stats';
import LavaMeaning from '../components/LavaMeaning';
import Founder from '../components/Founder';
import Craft from '../components/Craft';
import FAQ from '../components/FAQ';
import Gallery from '../components/Gallery';
import VIP from '../components/VIP';
import NanoAI from '../components/NanoAI';
import Footer from '../components/Footer';
import ChatBubble from '../components/chat/ChatBubble';

const REGISTRY = {
  hero: Hero,
  products: Products,
  story: Story,
  promise: Promise,
  chakra: Chakra,
  stats: Stats,
  lavaMeaning: LavaMeaning,
  founder: Founder,
  craft: Craft,
  faq: FAQ,
  gallery: Gallery,
  vip: VIP,
  nanoAI: NanoAI,
};

export default function Home() {
  const { site } = useSite();
  const baseOrder = site.sectionOrder || Object.keys(REGISTRY);
  // Append any registered sections missing from a saved order (e.g. newly added nanoAI)
  const order = [...baseOrder, ...Object.keys(REGISTRY).filter((k) => !baseOrder.includes(k))];
  const vis = site.sectionVisibility || {};
  return (
    <div className="min-h-screen bg-[#faf6f0]">
      <Navbar />
      {order.map((key) => {
        const C = REGISTRY[key];
        if (!C) return null;
        if (vis[key] === false) return null;
        return <C key={key} />;
      })}
      <Footer />
      <ChatBubble />
    </div>
  );
}
