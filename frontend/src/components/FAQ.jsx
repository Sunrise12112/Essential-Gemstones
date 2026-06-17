import React from 'react';
import { faqs } from '../mock';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from './ui/accordion';

export default function FAQ() {
  return (
    <section id="faq" className="py-24 md:py-32 bg-[#f3ece0]">
      <div className="max-w-4xl mx-auto px-6 md:px-10">
        <div className="text-center mb-14">
          <p className="text-xs tracking-[0.3em] uppercase text-[#8b6b4f] mb-4">FAQ</p>
          <h2 className="font-serif text-4xl md:text-5xl text-[#1a1410] mb-5 leading-tight">Frequently Asked <span className="italic">Questions</span></h2>
          <p className="text-[#5a4a3d]">Everything you need to know before your first — or next — order.</p>
        </div>

        <Accordion type="single" collapsible className="space-y-3">
          {faqs.map((f, i) => (
            <AccordionItem key={i} value={`item-${i}`} className="bg-[#faf6f0] border border-[#e8dfd1] rounded-2xl px-6 data-[state=open]:border-[#c9a876]">
              <AccordionTrigger className="font-serif text-lg md:text-xl text-[#1a1410] hover:no-underline py-5 text-left">
                {f.q}
              </AccordionTrigger>
              <AccordionContent className="text-[#5a4a3d] leading-relaxed pb-5">
                {f.a}
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </div>
    </section>
  );
}
