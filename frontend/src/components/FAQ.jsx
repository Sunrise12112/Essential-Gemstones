import React from 'react';
import { useSite } from '../context/SiteContext';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from './ui/accordion';

export default function FAQ() {
  const { site } = useSite();
  const f = site.faq || {};
  const items = f.items || [];
  return (
    <section id="faq" className="py-24 md:py-32 bg-[#f3ece0]">
      <div className="max-w-4xl mx-auto px-6 md:px-10">
        <div className="text-center mb-14">
          {f.kicker && <p className="text-xs tracking-[0.3em] uppercase text-[#8b6b4f] mb-4">{f.kicker}</p>}
          {f.title && <h2 className="font-serif text-4xl md:text-5xl text-[#1a1410] mb-5 leading-tight">{f.title}</h2>}
          {f.subtitle && <p className="text-[#5a4a3d]">{f.subtitle}</p>}
        </div>
        <Accordion type="single" collapsible className="space-y-3">
          {items.map((it, i) => (
            <AccordionItem key={i} value={`item-${i}`} className="bg-[#faf6f0] border border-[#e8dfd1] rounded-2xl px-6 data-[state=open]:border-[#c9a876]">
              <AccordionTrigger className="font-serif text-lg md:text-xl text-[#1a1410] hover:no-underline py-5 text-left">{it.q}</AccordionTrigger>
              <AccordionContent className="text-[#5a4a3d] leading-relaxed pb-5">{it.a}</AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </div>
    </section>
  );
}
