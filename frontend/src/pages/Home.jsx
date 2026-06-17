import React from 'react';
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
import Footer from '../components/Footer';

export default function Home() {
  return (
    <div className="min-h-screen bg-[#faf6f0]">
      <Navbar />
      <Hero />
      <Products />
      <Story />
      <Promise />
      <Chakra />
      <Stats />
      <LavaMeaning />
      <Founder />
      <Craft />
      <FAQ />
      <Gallery />
      <VIP />
      <Footer />
    </div>
  );
}
