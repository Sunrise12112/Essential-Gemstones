import React from 'react';

export function Field({ label, children }) {
  return (
    <div>
      <label className="block text-xs tracking-[0.2em] uppercase text-[#8b6b4f] mb-2">{label}</label>
      {children}
    </div>
  );
}

export function TextInput({ value, onChange, ...rest }) {
  return (
    <input value={value || ''} onChange={(e) => onChange(e.target.value)} {...rest} className="w-full px-4 py-2.5 border border-[#e8dfd1] rounded-lg focus:border-[#6b4f3a] focus:outline-none text-sm bg-white" />
  );
}

export function TextArea({ value, onChange, rows = 3, ...rest }) {
  return (
    <textarea value={value || ''} onChange={(e) => onChange(e.target.value)} rows={rows} {...rest} className="w-full px-4 py-2.5 border border-[#e8dfd1] rounded-lg focus:border-[#6b4f3a] focus:outline-none text-sm bg-white" />
  );
}

export function SectionCard({ title, children, open, onToggle, testId }) {
  const sectionId = testId || `admin-section-${title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/-$/, '')}`;
  return (
    <div className="bg-white border border-[#e8dfd1] rounded-2xl overflow-hidden">
      <button type="button" data-testid={`${sectionId}-toggle`} aria-expanded={!!open} aria-controls={`${sectionId}-content`} onClick={onToggle} className="w-full px-6 py-4 flex items-center justify-between hover:bg-[#faf6f0] transition-colors">
        <span className="font-serif text-lg text-[#1a1410]">{title}</span>
        <span className="text-[#8b6b4f] text-sm">{open ? '−' : '+'}</span>
      </button>
      {open && <div id={`${sectionId}-content`} data-testid={`${sectionId}-content`} className="px-6 pb-6 space-y-4 border-t border-[#e8dfd1]">{children}</div>}
    </div>
  );
}

export function ListReorder({ items, onMove, onRemove, onAdd, renderItem, addLabel = 'Add item' }) {
  return (
    <div className="space-y-3">
      {items.map((item, i) => (
        <div key={i} className="border border-[#e8dfd1] rounded-xl p-4 bg-[#faf6f0]">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs tracking-[0.2em] uppercase text-[#8b6b4f]">#{i + 1}</span>
            <div className="flex items-center gap-1">
              <button type="button" onClick={() => onMove(i, -1)} disabled={i === 0} className="px-2 py-1 text-xs border border-[#e8dfd1] rounded hover:bg-white disabled:opacity-40">↑</button>
              <button type="button" onClick={() => onMove(i, 1)} disabled={i === items.length - 1} className="px-2 py-1 text-xs border border-[#e8dfd1] rounded hover:bg-white disabled:opacity-40">↓</button>
              <button type="button" onClick={() => onRemove(i)} className="px-2 py-1 text-xs border border-red-300 text-red-700 rounded hover:bg-red-50">Delete</button>
            </div>
          </div>
          {renderItem(item, i)}
        </div>
      ))}
      <button type="button" onClick={onAdd} className="w-full py-2.5 border border-dashed border-[#c9a876] text-[#6b4f3a] rounded-xl text-sm hover:bg-[#faf0e0] transition-colors">+ {addLabel}</button>
    </div>
  );
}
