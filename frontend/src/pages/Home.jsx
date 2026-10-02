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
import Quiz from '../components/Quiz';
import CustomSection from '../components/CustomSection';
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
  quiz: Quiz,
};

export default function Home() {
  const { site } = useSite();
  const custom = Array.isArray(site.customSections) ? site.customSections : [];
  const customMap = Object.fromEntries(custom.map((s) => [s.id, s]));
  const baseOrder = site.sectionOrder || Object.keys(REGISTRY);
  // Append any registered sections or custom sections missing from a saved order.
  const order = [
    ...baseOrder,
    ...Object.keys(REGISTRY).filter((k) => !baseOrder.includes(k)),
    ...custom.map((s) => s.id).filter((id) => !baseOrder.includes(id)),
  ];
  const vis = site.sectionVisibility || {};
  return (
    <div className="min-h-screen bg-[#faf6f0]">
      <Navbar />
      {order.map((key) => {
        if (vis[key] === false) return null;
        const C = REGISTRY[key];
        if (C) return <C key={key} />;
        const cs = customMap[key];
        if (cs) return <CustomSection key={key} section={cs} />;
        return null;
      })}
      <Footer />
      <ChatBubble />
    </div>
  );
}
