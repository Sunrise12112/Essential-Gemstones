import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { LogOut, Save, Eye, RefreshCw, ChevronUp, ChevronDown, Users, ShieldCheck, Sparkles, Undo2, X } from 'lucide-react';
import api from '../lib/api';
import { useSite } from '../context/SiteContext';
import { useToast } from '../hooks/use-toast';
import { Field, TextInput, TextArea, SectionCard, ListReorder } from '../components/admin/FormControls';
import MediaPicker from '../components/admin/MediaPicker';
import AdminsManager from '../components/admin/AdminsManager';
import SubscribersManager from '../components/admin/SubscribersManager';
import UsersManager from '../components/admin/UsersManager';
import AIWriter from '../components/admin/AIWriter';
import { Switch } from '../components/ui/switch';

const SECTION_LABELS = {
  hero: 'Hero',
  products: 'Collection (Products)',
  story: 'Our Story',
  promise: 'Our Promise',
  chakra: 'Chakra Guide',
  stats: 'Best Sellers (Stats)',
  lavaMeaning: 'What Lava Stone Means',
  founder: 'Meet the Founder',
  craft: 'Craftsmanship',
  faq: 'FAQ',
  gallery: 'Gallery',
  vip: 'VIP Membership',
};

export default function AdminDashboard() {
  const navigate = useNavigate();
  const { site, loading: siteLoading, refresh } = useSite();
  const { toast } = useToast();
  const [data, setData] = useState(null);
  const [openSections, setOpenSections] = useState({ navbar: true });
  const [saving, setSaving] = useState(false);
  const [me, setMe] = useState(null);
  const [aiOpen, setAiOpen] = useState(false);
  const [lastAiEdit, setLastAiEdit] = useState(null); // { summary, applied, snapshot, at }
  const [undoing, setUndoing] = useState(false);

  useEffect(() => {
    const onEdit = (e) => setLastAiEdit(e.detail || null);
    const onUndone = () => setLastAiEdit(null);
    window.addEventListener('eg:ai-edit', onEdit);
    window.addEventListener('eg:ai-edit-undone', onUndone);
    return () => {
      window.removeEventListener('eg:ai-edit', onEdit);
      window.removeEventListener('eg:ai-edit-undone', onUndone);
    };
  }, []);

  const undoLastAiEdit = async () => {
    if (!lastAiEdit?.snapshot) return;
    setUndoing(true);
    try {
      await api.post('/admin/ai-edit/undo', { snapshot: lastAiEdit.snapshot });
      await refresh();
      setLastAiEdit(null);
      toast({ title: 'Reverted', description: 'Site restored to the previous version.' });
    } catch (err) {
      toast({ title: 'Undo failed', description: err?.response?.data?.detail || 'Try again.', variant: 'destructive' });
    } finally {
      setUndoing(false);
    }
  };

  useEffect(() => {
    if (!localStorage.getItem('eg_admin_token')) {
      navigate('/admin');
      return;
    }
    api.get('/admin/me').then((res) => {
      setMe(res.data?.user || null);
    }).catch(() => {
      localStorage.removeItem('eg_admin_token');
      localStorage.removeItem('eg_admin_user');
      navigate('/admin');
    });
  }, [navigate]);

  const can = (key) => {
    if (!me) return false;
    if (me.isSuper) return true;
    return (me.permissions || []).includes(key);
  };

  useEffect(() => {
    // Only seed the editor once the real site data has loaded — never from defaults,
    // otherwise saving would overwrite the DB with stale/default content.
    if (!siteLoading && site && !data) setData(JSON.parse(JSON.stringify(site)));
  }, [site, siteLoading, data]);

  if (!data) {
    return <div className="min-h-screen flex items-center justify-center bg-[#faf6f0]"><RefreshCw className="w-6 h-6 animate-spin text-[#6b4f3a]" /></div>;
  }

  const update = (path, value) => {
    setData((prev) => {
      const next = JSON.parse(JSON.stringify(prev));
      let cur = next;
      for (let i = 0; i < path.length - 1; i++) cur = cur[path[i]];
      cur[path[path.length - 1]] = value;
      return next;
    });
  };

  const toggle = (k) => setOpenSections((s) => ({ ...s, [k]: !s[k] }));

  const save = async () => {
    setSaving(true);
    try {
      await api.put('/site', data);
      await refresh();
      toast({ title: 'Saved', description: 'Your changes are live.' });
    } catch (err) {
      toast({ title: 'Save failed', description: err?.response?.data?.detail || 'Try again.', variant: 'destructive' });
    } finally {
      setSaving(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('eg_admin_token');
    localStorage.removeItem('eg_admin_user');
    navigate('/admin');
  };

  // Section order
  const moveSection = (idx, dir) => {
    const order = [...(data.sectionOrder || [])];
    const j = idx + dir;
    if (j < 0 || j >= order.length) return;
    [order[idx], order[j]] = [order[j], order[idx]];
    update(['sectionOrder'], order);
  };
  const setVis = (key, v) => update(['sectionVisibility', key], v);

  return (
    <div className="min-h-screen bg-[#faf6f0]">
      <header className="sticky top-0 z-40 bg-[#1a1410] text-[#faf6f0] border-b border-[#3d2f24]">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between gap-4">
          <div>
            <h1 className="font-serif text-xl">Site Editor</h1>
            <p className="text-xs text-[#bfae95]">
              {me ? <>Signed in as <span className="text-[#c9a876]">{me.username}</span>{me.isSuper && <span className="ml-1 inline-flex items-center gap-1"><ShieldCheck className="w-3 h-3" />super</span>}</> : 'Essential Gemstones CMS'}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => setAiOpen(true)} className="inline-flex items-center gap-2 px-4 py-2 text-sm bg-[#c9a876]/15 border border-[#c9a876]/40 text-[#c9a876] rounded-full hover:bg-[#c9a876]/25" title="Write with AI"><Sparkles className="w-4 h-4" /> <span className="hidden sm:inline">AI Writer</span></button>
            <Link to="/" target="_blank" className="inline-flex items-center gap-2 px-4 py-2 text-sm border border-[#3d2f24] rounded-full hover:bg-[#241b15]"><Eye className="w-4 h-4" /> View site</Link>
            <button onClick={save} disabled={saving} className="inline-flex items-center gap-2 px-5 py-2 bg-[#c9a876] text-[#1a1410] rounded-full text-sm font-medium hover:bg-[#d6b885] disabled:opacity-60">
              {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Save changes
            </button>
            <button onClick={logout} className="inline-flex items-center gap-2 px-4 py-2 text-sm border border-[#3d2f24] rounded-full hover:bg-[#241b15]"><LogOut className="w-4 h-4" /></button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-10 space-y-4">
        {/* Global "undo last AI edit" banner */}
        {lastAiEdit && lastAiEdit.snapshot && (
          <div data-testid="ai-undo-banner" className="sticky top-[76px] z-30 flex items-center justify-between gap-4 bg-[#1a1410] border border-[#c9a876]/40 text-[#faf6f0] rounded-2xl px-5 py-3 shadow-xl animate-in slide-in-from-top-4">
            <div className="flex items-center gap-3 min-w-0">
              <span className="w-8 h-8 rounded-full bg-[#c9a876]/20 flex items-center justify-center shrink-0"><Sparkles className="w-4 h-4 text-[#c9a876]" /></span>
              <div className="min-w-0">
                <p className="text-xs tracking-[0.2em] uppercase text-[#c9a876]">AI just edited your site</p>
                <p className="text-sm text-[#faf6f0] truncate">{lastAiEdit.summary || `${(lastAiEdit.applied || []).length} change(s) applied.`}</p>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={undoLastAiEdit}
                disabled={undoing}
                data-testid="ai-undo-banner-btn"
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-[#c9a876] text-[#1a1410] text-sm font-medium hover:bg-[#d6b885] disabled:opacity-60">
                {undoing ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Undo2 className="w-4 h-4" />} Undo
              </button>
              <button onClick={() => setLastAiEdit(null)} aria-label="Dismiss" data-testid="ai-undo-banner-dismiss" className="w-8 h-8 rounded-full hover:bg-[#241b15] flex items-center justify-center">
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* Section ordering */}
        {can('sectionOrder') && (
        <SectionCard title="Section Order & Visibility" open={openSections.order} onToggle={() => toggle('order')}>
          <p className="text-sm text-[#5a4a3d] -mt-1">Reorder sections on the home page, or hide them.</p>
          <div className="space-y-2">
            {(data.sectionOrder || []).map((key, i) => (
              <div key={key} className="flex items-center justify-between border border-[#e8dfd1] rounded-xl px-4 py-3 bg-[#faf6f0]">
                <div className="flex items-center gap-3">
                  <span className="text-xs tracking-[0.2em] uppercase text-[#8b6b4f] w-6">{i + 1}</span>
                  <span className="font-serif text-base text-[#1a1410]">{SECTION_LABELS[key] || key}</span>
                </div>
                <div className="flex items-center gap-3">
                  <Switch checked={data.sectionVisibility?.[key] !== false} onCheckedChange={(v) => setVis(key, v)} />
                  <button type="button" onClick={() => moveSection(i, -1)} disabled={i === 0} className="p-1.5 border border-[#e8dfd1] rounded hover:bg-white disabled:opacity-40"><ChevronUp className="w-4 h-4" /></button>
                  <button type="button" onClick={() => moveSection(i, 1)} disabled={i === data.sectionOrder.length - 1} className="p-1.5 border border-[#e8dfd1] rounded hover:bg-white disabled:opacity-40"><ChevronDown className="w-4 h-4" /></button>
                </div>
              </div>
            ))}
          </div>
        </SectionCard>
        )}

        {/* Manage admins (super only) */}
        {me?.isSuper && (
          <SectionCard title="Manage Admins" open={openSections.admins} onToggle={() => toggle('admins')}>
            <AdminsManager currentUser={me} />
          </SectionCard>
        )}

        {/* Subscribers */}
        {can('manage_subscribers') && (
          <SectionCard title="Newsletter Subscribers" open={openSections.subscribers} onToggle={() => toggle('subscribers')}>
            <SubscribersManager isSuper={!!me?.isSuper} />
          </SectionCard>
        )}

        {/* Members / Users */}
        {can('manage_users') && (
          <SectionCard title="Members (User Accounts)" open={openSections.members} onToggle={() => toggle('members')}>
            <UsersManager />
          </SectionCard>
        )}

        {/* Navbar */}
        {can('navbar') && (
        <SectionCard title="Navigation Menu" open={openSections.navbar} onToggle={() => toggle('navbar')}>
          <div className="grid sm:grid-cols-2 gap-4">
            <Field label="Brand name"><TextInput value={data.navbar.brand} onChange={(v) => update(['navbar', 'brand'], v)} /></Field>
            <Field label="CTA button label"><TextInput value={data.navbar.ctaLabel} onChange={(v) => update(['navbar', 'ctaLabel'], v)} /></Field>
            <Field label="CTA button link"><TextInput value={data.navbar.ctaHref} onChange={(v) => update(['navbar', 'ctaHref'], v)} /></Field>
          </div>
          <Field label="Menu links">
            <ListReorder
              items={data.navbar.links || []}
              onMove={(i, d) => { const arr = [...data.navbar.links]; const j = i + d; if (j<0||j>=arr.length) return; [arr[i],arr[j]]=[arr[j],arr[i]]; update(['navbar','links'], arr); }}
              onRemove={(i) => update(['navbar','links'], data.navbar.links.filter((_, x) => x !== i))}
              onAdd={() => update(['navbar','links'], [...(data.navbar.links||[]), { label: 'New link', href: '#' }])}
              addLabel="Add menu link"
              renderItem={(item, i) => (
                <div className="grid sm:grid-cols-2 gap-3">
                  <TextInput value={item.label} onChange={(v) => { const arr=[...data.navbar.links]; arr[i]={...arr[i],label:v}; update(['navbar','links'],arr); }} placeholder="Label" />
                  <TextInput value={item.href} onChange={(v) => { const arr=[...data.navbar.links]; arr[i]={...arr[i],href:v}; update(['navbar','links'],arr); }} placeholder="#anchor or URL" />
                </div>
              )}
            />
          </Field>
        </SectionCard>
        )}

        {/* Hero */}
        {can('hero') && (
        <SectionCard title="Hero" open={openSections.hero} onToggle={() => toggle('hero')}>
          <Field label="Kicker (small uppercase text)"><TextInput value={data.hero.kicker} onChange={(v) => update(['hero','kicker'], v)} /></Field>
          <div className="grid sm:grid-cols-2 gap-4">
            <Field label="Title line 1"><TextInput value={data.hero.titleLine1} onChange={(v) => update(['hero','titleLine1'], v)} /></Field>
            <Field label="Title line 2 (italic)"><TextInput value={data.hero.titleLine2} onChange={(v) => update(['hero','titleLine2'], v)} /></Field>
          </div>
          <Field label="Subtitle"><TextArea value={data.hero.subtitle} onChange={(v) => update(['hero','subtitle'], v)} rows={3} /></Field>
          <div className="grid sm:grid-cols-2 gap-4">
            <Field label="Primary CTA label"><TextInput value={data.hero.ctaPrimary?.label} onChange={(v) => update(['hero','ctaPrimary'], { ...data.hero.ctaPrimary, label: v })} /></Field>
            <Field label="Primary CTA link"><TextInput value={data.hero.ctaPrimary?.href} onChange={(v) => update(['hero','ctaPrimary'], { ...data.hero.ctaPrimary, href: v })} /></Field>
            <Field label="Secondary CTA label"><TextInput value={data.hero.ctaSecondary?.label} onChange={(v) => update(['hero','ctaSecondary'], { ...data.hero.ctaSecondary, label: v })} /></Field>
            <Field label="Secondary CTA link"><TextInput value={data.hero.ctaSecondary?.href} onChange={(v) => update(['hero','ctaSecondary'], { ...data.hero.ctaSecondary, href: v })} /></Field>
          </div>
          <div className="bg-[#faf6f0] border border-[#e8dfd1] rounded-xl p-4 space-y-3">
            <p className="font-serif text-sm text-[#1a1410]">Featured media (oval) \u2014 image or video</p>
            <Field label="Media type">
              <div className="flex gap-3">
                {['image', 'video'].map((t) => (
                  <button key={t} type="button" onClick={() => update(['hero','mediaType'], t)} className={`px-4 py-2 rounded-full text-sm border ${data.hero.mediaType === t ? 'bg-[#1a1410] text-[#faf6f0] border-[#1a1410]' : 'border-[#e8dfd1] hover:bg-white'}`}>{t}</button>
                ))}
              </div>
            </Field>
            <MediaPicker value={data.hero.mediaUrl} onChange={(url, kind) => { update(['hero','mediaUrl'], url); if (kind) update(['hero','mediaType'], kind); }} label="Featured media file" />
          </div>
          <div className="grid sm:grid-cols-2 gap-4">
            <Field label="Quote text"><TextInput value={data.hero.quoteText} onChange={(v) => update(['hero','quoteText'], v)} /></Field>
            <Field label="Quote author"><TextInput value={data.hero.quoteAuthor} onChange={(v) => update(['hero','quoteAuthor'], v)} /></Field>
          </div>
        </SectionCard>
        )}

        {/* Products */}
        {can('products') && (
        <SectionCard title="Collection (Products)" open={openSections.products} onToggle={() => toggle('products')}>
          <Field label="Kicker"><TextInput value={data.products.kicker} onChange={(v) => update(['products','kicker'], v)} /></Field>
          <Field label="Title"><TextInput value={data.products.title} onChange={(v) => update(['products','title'], v)} /></Field>
          <Field label="Subtitle"><TextArea value={data.products.subtitle} onChange={(v) => update(['products','subtitle'], v)} rows={2} /></Field>
          <Field label="Products">
            <ListReorder
              items={data.products.items || []}
              onMove={(i, d) => { const arr=[...data.products.items]; const j=i+d; if(j<0||j>=arr.length) return; [arr[i],arr[j]]=[arr[j],arr[i]]; update(['products','items'], arr); }}
              onRemove={(i) => update(['products','items'], data.products.items.filter((_,x) => x !== i))}
              onAdd={() => update(['products','items'], [...(data.products.items||[]), { id: `p-${Date.now()}`, name: 'New product', price: '$0', image: '', description: '', buyUrl: '', badge: 'New' }])}
              addLabel="Add product"
              renderItem={(item, i) => (
                <div className="space-y-3">
                  <div className="grid sm:grid-cols-2 gap-3">
                    <TextInput value={item.name} placeholder="Name" onChange={(v) => { const arr=[...data.products.items]; arr[i]={...arr[i],name:v}; update(['products','items'],arr); }} />
                    <TextInput value={item.price} placeholder="Price" onChange={(v) => { const arr=[...data.products.items]; arr[i]={...arr[i],price:v}; update(['products','items'],arr); }} />
                  </div>
                  <TextArea value={item.description} placeholder="Description" rows={2} onChange={(v) => { const arr=[...data.products.items]; arr[i]={...arr[i],description:v}; update(['products','items'],arr); }} />
                  <div className="grid sm:grid-cols-2 gap-3">
                    <TextInput value={item.buyUrl} placeholder="Buy link (Stripe)" onChange={(v) => { const arr=[...data.products.items]; arr[i]={...arr[i],buyUrl:v}; update(['products','items'],arr); }} />
                    <TextInput value={item.badge} placeholder="Badge (e.g. New)" onChange={(v) => { const arr=[...data.products.items]; arr[i]={...arr[i],badge:v}; update(['products','items'],arr); }} />
                  </div>
                  <MediaPicker value={item.image} onChange={(url) => { const arr=[...data.products.items]; arr[i]={...arr[i],image:url}; update(['products','items'],arr); }} label="Image" accept="image/*" />
                </div>
              )}
            />
          </Field>
        </SectionCard>
        )}

        {/* Story */}
        {can('story') && (
        <SectionCard title="Our Story" open={openSections.story} onToggle={() => toggle('story')}>
          <Field label="Kicker"><TextInput value={data.story.kicker} onChange={(v) => update(['story','kicker'], v)} /></Field>
          <Field label="Title"><TextInput value={data.story.title} onChange={(v) => update(['story','title'], v)} /></Field>
          <Field label="Floating badge text"><TextInput value={data.story.badge} onChange={(v) => update(['story','badge'], v)} /></Field>
          <MediaPicker value={data.story.image} onChange={(url) => update(['story','image'], url)} label="Story image" accept="image/*" />
          <Field label="Paragraphs">
            <ListReorder
              items={data.story.paragraphs || []}
              onMove={(i, d) => { const arr=[...data.story.paragraphs]; const j=i+d; if(j<0||j>=arr.length) return; [arr[i],arr[j]]=[arr[j],arr[i]]; update(['story','paragraphs'], arr); }}
              onRemove={(i) => update(['story','paragraphs'], data.story.paragraphs.filter((_,x) => x !== i))}
              onAdd={() => update(['story','paragraphs'], [...(data.story.paragraphs||[]), 'New paragraph'])}
              addLabel="Add paragraph"
              renderItem={(p, i) => (
                <TextArea value={p} rows={3} onChange={(v) => { const arr=[...data.story.paragraphs]; arr[i]=v; update(['story','paragraphs'],arr); }} />
              )}
            />
          </Field>
        </SectionCard>
        )}

        {/* Promise */}
        {can('promise') && (
        <SectionCard title="Our Promise" open={openSections.promise} onToggle={() => toggle('promise')}>
          <Field label="Kicker"><TextInput value={data.promise.kicker} onChange={(v) => update(['promise','kicker'], v)} /></Field>
          <Field label="Title"><TextInput value={data.promise.title} onChange={(v) => update(['promise','title'], v)} /></Field>
          <Field label="Body"><TextArea value={data.promise.body} onChange={(v) => update(['promise','body'], v)} rows={4} /></Field>
        </SectionCard>
        )}

        {/* Chakra */}
        {can('chakra') && (
        <SectionCard title="Chakra Guide" open={openSections.chakra} onToggle={() => toggle('chakra')}>
          <Field label="Kicker"><TextInput value={data.chakra.kicker} onChange={(v) => update(['chakra','kicker'], v)} /></Field>
          <Field label="Title"><TextInput value={data.chakra.title} onChange={(v) => update(['chakra','title'], v)} /></Field>
          <Field label="Subtitle"><TextArea value={data.chakra.subtitle} onChange={(v) => update(['chakra','subtitle'], v)} rows={3} /></Field>
          <Field label="Footer note"><TextArea value={data.chakra.footer} onChange={(v) => update(['chakra','footer'], v)} rows={2} /></Field>
          <Field label="Stones">
            <ListReorder
              items={data.chakra.stones || []}
              onMove={(i, d) => { const arr=[...data.chakra.stones]; const j=i+d; if(j<0||j>=arr.length) return; [arr[i],arr[j]]=[arr[j],arr[i]]; update(['chakra','stones'], arr); }}
              onRemove={(i) => update(['chakra','stones'], data.chakra.stones.filter((_,x) => x !== i))}
              onAdd={() => update(['chakra','stones'], [...(data.chakra.stones||[]), { stone: 'New stone', chakra: '', color: '#888', desc: '' }])}
              addLabel="Add stone"
              renderItem={(s, i) => (
                <div className="space-y-2">
                  <div className="grid sm:grid-cols-3 gap-2">
                    <TextInput value={s.stone} placeholder="Stone name" onChange={(v) => { const a=[...data.chakra.stones]; a[i]={...a[i],stone:v}; update(['chakra','stones'],a); }} />
                    <TextInput value={s.chakra} placeholder="Chakra" onChange={(v) => { const a=[...data.chakra.stones]; a[i]={...a[i],chakra:v}; update(['chakra','stones'],a); }} />
                    <div className="flex items-center gap-2">
                      <input type="color" value={s.color || '#888'} onChange={(e) => { const a=[...data.chakra.stones]; a[i]={...a[i],color:e.target.value}; update(['chakra','stones'],a); }} className="w-10 h-10 border rounded" />
                      <TextInput value={s.color} placeholder="#hex" onChange={(v) => { const a=[...data.chakra.stones]; a[i]={...a[i],color:v}; update(['chakra','stones'],a); }} />
                    </div>
                  </div>
                  <TextArea value={s.desc} placeholder="Description" rows={2} onChange={(v) => { const a=[...data.chakra.stones]; a[i]={...a[i],desc:v}; update(['chakra','stones'],a); }} />
                </div>
              )}
            />
          </Field>
        </SectionCard>
        )}

        {/* Stats */}
        {can('stats') && (
        <SectionCard title="Best Sellers (Stats)" open={openSections.stats} onToggle={() => toggle('stats')}>
          <Field label="Kicker"><TextInput value={data.stats.kicker} onChange={(v) => update(['stats','kicker'], v)} /></Field>
          <Field label="Title"><TextInput value={data.stats.title} onChange={(v) => update(['stats','title'], v)} /></Field>
          <Field label="Stats">
            <ListReorder
              items={data.stats.items || []}
              onMove={(i, d) => { const arr=[...data.stats.items]; const j=i+d; if(j<0||j>=arr.length) return; [arr[i],arr[j]]=[arr[j],arr[i]]; update(['stats','items'], arr); }}
              onRemove={(i) => update(['stats','items'], data.stats.items.filter((_,x) => x !== i))}
              onAdd={() => update(['stats','items'], [...(data.stats.items||[]), { number: '0', label: 'New', sub: '' }])}
              addLabel="Add stat"
              renderItem={(s, i) => (
                <div className="space-y-2">
                  <div className="grid sm:grid-cols-2 gap-2">
                    <TextInput value={s.number} placeholder="Big number" onChange={(v) => { const a=[...data.stats.items]; a[i]={...a[i],number:v}; update(['stats','items'],a); }} />
                    <TextInput value={s.label} placeholder="Label" onChange={(v) => { const a=[...data.stats.items]; a[i]={...a[i],label:v}; update(['stats','items'],a); }} />
                  </div>
                  <TextArea value={s.sub} placeholder="Sub text" rows={2} onChange={(v) => { const a=[...data.stats.items]; a[i]={...a[i],sub:v}; update(['stats','items'],a); }} />
                </div>
              )}
            />
          </Field>
        </SectionCard>
        )}

        {/* Lava Meaning */}
        {can('lavaMeaning') && (
        <SectionCard title="What Lava Stone Means" open={openSections.lavaMeaning} onToggle={() => toggle('lavaMeaning')}>
          <Field label="Kicker"><TextInput value={data.lavaMeaning.kicker} onChange={(v) => update(['lavaMeaning','kicker'], v)} /></Field>
          <Field label="Title"><TextInput value={data.lavaMeaning.title} onChange={(v) => update(['lavaMeaning','title'], v)} /></Field>
          <Field label="Subtitle"><TextArea value={data.lavaMeaning.subtitle} onChange={(v) => update(['lavaMeaning','subtitle'], v)} rows={2} /></Field>
          <Field label="Items">
            <ListReorder
              items={data.lavaMeaning.items || []}
              onMove={(i, d) => { const arr=[...data.lavaMeaning.items]; const j=i+d; if(j<0||j>=arr.length) return; [arr[i],arr[j]]=[arr[j],arr[i]]; update(['lavaMeaning','items'], arr); }}
              onRemove={(i) => update(['lavaMeaning','items'], data.lavaMeaning.items.filter((_,x) => x !== i))}
              onAdd={() => update(['lavaMeaning','items'], [...(data.lavaMeaning.items||[]), { title: 'New', icon: 'Sparkles', desc: '' }])}
              addLabel="Add card"
              renderItem={(m, i) => (
                <div className="space-y-2">
                  <div className="grid sm:grid-cols-2 gap-2">
                    <TextInput value={m.title} placeholder="Title" onChange={(v) => { const a=[...data.lavaMeaning.items]; a[i]={...a[i],title:v}; update(['lavaMeaning','items'],a); }} />
                    <TextInput value={m.icon} placeholder="Icon (Mountain, Flame, Leaf, Shield, Sparkles, Heart, Lightbulb, Star, Gem)" onChange={(v) => { const a=[...data.lavaMeaning.items]; a[i]={...a[i],icon:v}; update(['lavaMeaning','items'],a); }} />
                  </div>
                  <TextArea value={m.desc} placeholder="Description" rows={2} onChange={(v) => { const a=[...data.lavaMeaning.items]; a[i]={...a[i],desc:v}; update(['lavaMeaning','items'],a); }} />
                </div>
              )}
            />
          </Field>
        </SectionCard>
        )}

        {/* Founder */}
        {can('founder') && (
        <SectionCard title="Meet the Founder" open={openSections.founder} onToggle={() => toggle('founder')}>
          <Field label="Kicker"><TextInput value={data.founder.kicker} onChange={(v) => update(['founder','kicker'], v)} /></Field>
          <Field label="Title"><TextInput value={data.founder.title} onChange={(v) => update(['founder','title'], v)} /></Field>
          <Field label="Intro"><TextArea value={data.founder.intro} onChange={(v) => update(['founder','intro'], v)} rows={3} /></Field>
          <div className="grid sm:grid-cols-2 gap-4">
            <Field label="Age badge (big)"><TextInput value={data.founder.ageBadge} onChange={(v) => update(['founder','ageBadge'], v)} /></Field>
            <Field label="Age label"><TextInput value={data.founder.ageLabel} onChange={(v) => update(['founder','ageLabel'], v)} /></Field>
          </div>
          <MediaPicker value={data.founder.image} onChange={(url) => update(['founder','image'], url)} label="Founder photo" accept="image/*" />
          <Field label="Highlight blocks">
            <ListReorder
              items={data.founder.blocks || []}
              onMove={(i, d) => { const arr=[...data.founder.blocks]; const j=i+d; if(j<0||j>=arr.length) return; [arr[i],arr[j]]=[arr[j],arr[i]]; update(['founder','blocks'], arr); }}
              onRemove={(i) => update(['founder','blocks'], data.founder.blocks.filter((_,x) => x !== i))}
              onAdd={() => update(['founder','blocks'], [...(data.founder.blocks||[]), { icon: 'Sparkles', title: 'New', desc: '' }])}
              addLabel="Add block"
              renderItem={(b, i) => (
                <div className="space-y-2">
                  <div className="grid sm:grid-cols-2 gap-2">
                    <TextInput value={b.icon} placeholder="Icon (Sparkles, Heart, Lightbulb, Star, Gem)" onChange={(v) => { const a=[...data.founder.blocks]; a[i]={...a[i],icon:v}; update(['founder','blocks'],a); }} />
                    <TextInput value={b.title} placeholder="Title" onChange={(v) => { const a=[...data.founder.blocks]; a[i]={...a[i],title:v}; update(['founder','blocks'],a); }} />
                  </div>
                  <TextArea value={b.desc} placeholder="Description" rows={2} onChange={(v) => { const a=[...data.founder.blocks]; a[i]={...a[i],desc:v}; update(['founder','blocks'],a); }} />
                </div>
              )}
            />
          </Field>
        </SectionCard>
        )}

        {/* Craft */}
        {can('craft') && (
        <SectionCard title="Craftsmanship" open={openSections.craft} onToggle={() => toggle('craft')}>
          <Field label="Kicker"><TextInput value={data.craft.kicker} onChange={(v) => update(['craft','kicker'], v)} /></Field>
          <Field label="Title"><TextInput value={data.craft.title} onChange={(v) => update(['craft','title'], v)} /></Field>
          <Field label="Subtitle"><TextArea value={data.craft.subtitle} onChange={(v) => update(['craft','subtitle'], v)} rows={3} /></Field>
          <MediaPicker value={data.craft.image} onChange={(url) => update(['craft','image'], url)} label="Craft image" accept="image/*" />
          <Field label="Steps">
            <ListReorder
              items={data.craft.steps || []}
              onMove={(i, d) => { const arr=[...data.craft.steps]; const j=i+d; if(j<0||j>=arr.length) return; [arr[i],arr[j]]=[arr[j],arr[i]]; update(['craft','steps'], arr); }}
              onRemove={(i) => update(['craft','steps'], data.craft.steps.filter((_,x) => x !== i))}
              onAdd={() => update(['craft','steps'], [...(data.craft.steps||[]), { number: String(data.craft.steps.length + 1).padStart(2, '0'), title: 'New step', desc: '' }])}
              addLabel="Add step"
              renderItem={(s, i) => (
                <div className="space-y-2">
                  <div className="grid sm:grid-cols-3 gap-2">
                    <TextInput value={s.number} placeholder="01" onChange={(v) => { const a=[...data.craft.steps]; a[i]={...a[i],number:v}; update(['craft','steps'],a); }} />
                    <div className="sm:col-span-2"><TextInput value={s.title} placeholder="Title" onChange={(v) => { const a=[...data.craft.steps]; a[i]={...a[i],title:v}; update(['craft','steps'],a); }} /></div>
                  </div>
                  <TextArea value={s.desc} placeholder="Description" rows={2} onChange={(v) => { const a=[...data.craft.steps]; a[i]={...a[i],desc:v}; update(['craft','steps'],a); }} />
                </div>
              )}
            />
          </Field>
        </SectionCard>
        )}

        {/* FAQ */}
        {can('faq') && (
        <SectionCard title="FAQ" open={openSections.faq} onToggle={() => toggle('faq')}>
          <Field label="Kicker"><TextInput value={data.faq.kicker} onChange={(v) => update(['faq','kicker'], v)} /></Field>
          <Field label="Title"><TextInput value={data.faq.title} onChange={(v) => update(['faq','title'], v)} /></Field>
          <Field label="Subtitle"><TextInput value={data.faq.subtitle} onChange={(v) => update(['faq','subtitle'], v)} /></Field>
          <Field label="Questions">
            <ListReorder
              items={data.faq.items || []}
              onMove={(i, d) => { const arr=[...data.faq.items]; const j=i+d; if(j<0||j>=arr.length) return; [arr[i],arr[j]]=[arr[j],arr[i]]; update(['faq','items'], arr); }}
              onRemove={(i) => update(['faq','items'], data.faq.items.filter((_,x) => x !== i))}
              onAdd={() => update(['faq','items'], [...(data.faq.items||[]), { q: 'New question?', a: '' }])}
              addLabel="Add FAQ"
              renderItem={(it, i) => (
                <div className="space-y-2">
                  <TextInput value={it.q} placeholder="Question" onChange={(v) => { const a=[...data.faq.items]; a[i]={...a[i],q:v}; update(['faq','items'],a); }} />
                  <TextArea value={it.a} placeholder="Answer" rows={3} onChange={(v) => { const a=[...data.faq.items]; a[i]={...a[i],a:v}; update(['faq','items'],a); }} />
                </div>
              )}
            />
          </Field>
        </SectionCard>
        )}

        {/* Gallery */}
        {can('gallery') && (
        <SectionCard title="Gallery" open={openSections.gallery} onToggle={() => toggle('gallery')}>
          <Field label="Kicker"><TextInput value={data.gallery.kicker} onChange={(v) => update(['gallery','kicker'], v)} /></Field>
          <Field label="Title"><TextInput value={data.gallery.title} onChange={(v) => update(['gallery','title'], v)} /></Field>
          <Field label="Images">
            <ListReorder
              items={data.gallery.images || []}
              onMove={(i, d) => { const arr=[...data.gallery.images]; const j=i+d; if(j<0||j>=arr.length) return; [arr[i],arr[j]]=[arr[j],arr[i]]; update(['gallery','images'], arr); }}
              onRemove={(i) => update(['gallery','images'], data.gallery.images.filter((_,x) => x !== i))}
              onAdd={() => update(['gallery','images'], [...(data.gallery.images||[]), ''])}
              addLabel="Add image"
              renderItem={(img, i) => (
                <MediaPicker value={img} onChange={(url) => { const a=[...data.gallery.images]; a[i]=url; update(['gallery','images'],a); }} label={`Image ${i+1}`} accept="image/*" />
              )}
            />
          </Field>
        </SectionCard>
        )}

        {/* VIP */}
        {can('vip') && (
        <SectionCard title="VIP Membership" open={openSections.vip} onToggle={() => toggle('vip')}>
          <Field label="Kicker"><TextInput value={data.vip.kicker} onChange={(v) => update(['vip','kicker'], v)} /></Field>
          <Field label="Title"><TextInput value={data.vip.title} onChange={(v) => update(['vip','title'], v)} /></Field>
          <Field label="Subtitle"><TextArea value={data.vip.subtitle} onChange={(v) => update(['vip','subtitle'], v)} rows={2} /></Field>
          <div className="grid sm:grid-cols-2 gap-4">
            <Field label="CTA label"><TextInput value={data.vip.ctaLabel} onChange={(v) => update(['vip','ctaLabel'], v)} /></Field>
            <Field label="CTA URL"><TextInput value={data.vip.ctaUrl} onChange={(v) => update(['vip','ctaUrl'], v)} /></Field>
          </div>
          <Field label="Perks (public — shown to everyone)">
            <ListReorder
              items={data.vip.perks || []}
              onMove={(i, d) => { const arr=[...data.vip.perks]; const j=i+d; if(j<0||j>=arr.length) return; [arr[i],arr[j]]=[arr[j],arr[i]]; update(['vip','perks'], arr); }}
              onRemove={(i) => update(['vip','perks'], data.vip.perks.filter((_,x) => x !== i))}
              onAdd={() => update(['vip','perks'], [...(data.vip.perks||[]), { icon: 'Gift', label: 'New perk' }])}
              addLabel="Add public perk"
              renderItem={(p, i) => (
                <div className="grid sm:grid-cols-2 gap-2">
                  <TextInput value={p.icon} placeholder="Icon (Gift, Star, MessageCircle, Heart, Sparkles, Crown)" onChange={(v) => { const a=[...data.vip.perks]; a[i]={...a[i],icon:v}; update(['vip','perks'],a); }} />
                  <TextInput value={p.label} placeholder="Label" onChange={(v) => { const a=[...data.vip.perks]; a[i]={...a[i],label:v}; update(['vip','perks'],a); }} />
                </div>
              )}
            />
          </Field>

          <div className="pt-4 border-t border-[#e8dfd1]">
            <p className="text-xs tracking-[0.2em] uppercase text-[#8b6b4f] mb-1">Members-only content</p>
            <p className="text-sm text-[#5a4a3d] mb-4">Shown only after a visitor is signed in. Leave any field blank to hide it. Use <code className="bg-[#faf6f0] px-1.5 py-0.5 rounded text-[#6b4f3a]">{'{name}'}</code> in the greeting to auto-insert the member&rsquo;s first name. Wrap text in <code className="bg-[#faf6f0] px-1.5 py-0.5 rounded text-[#6b4f3a]">**double asterisks**</code> to make it bold.</p>
            <div className="grid sm:grid-cols-2 gap-4">
              <Field label="Members kicker"><TextInput value={data.vip.memberKicker} onChange={(v) => update(['vip','memberKicker'], v)} placeholder="Members Only" /></Field>
              <Field label="Greeting"><TextInput value={data.vip.memberGreeting} onChange={(v) => update(['vip','memberGreeting'], v)} placeholder="Welcome, {name}." /></Field>
            </div>
            <Field label="Intro paragraph"><TextArea value={data.vip.memberIntro} onChange={(v) => update(['vip','memberIntro'], v)} rows={2} /></Field>
            <Field label="Member perks (shown as a list)">
              <ListReorder
                items={data.vip.memberPerks || []}
                onMove={(i, d) => { const arr=[...(data.vip.memberPerks||[])]; const j=i+d; if(j<0||j>=arr.length) return; [arr[i],arr[j]]=[arr[j],arr[i]]; update(['vip','memberPerks'], arr); }}
                onRemove={(i) => update(['vip','memberPerks'], (data.vip.memberPerks||[]).filter((_,x) => x !== i))}
                onAdd={() => update(['vip','memberPerks'], [...(data.vip.memberPerks||[]), { icon: 'Star', title: 'New perk', desc: '' }])}
                addLabel="Add member perk"
                renderItem={(mp, i) => (
                  <div className="space-y-2">
                    <div className="grid sm:grid-cols-2 gap-2">
                      <TextInput value={mp.icon} placeholder="Icon (Star, Gift, Heart, MessageCircle, Sparkles, Crown, Gem)" onChange={(v) => { const a=[...(data.vip.memberPerks||[])]; a[i]={...a[i],icon:v}; update(['vip','memberPerks'],a); }} />
                      <TextInput value={mp.title} placeholder="Title (e.g. Member code)" onChange={(v) => { const a=[...(data.vip.memberPerks||[])]; a[i]={...a[i],title:v}; update(['vip','memberPerks'],a); }} />
                    </div>
                    <TextArea value={mp.desc} placeholder="Description (use **bold** if needed)" rows={2} onChange={(v) => { const a=[...(data.vip.memberPerks||[])]; a[i]={...a[i],desc:v}; update(['vip','memberPerks'],a); }} />
                  </div>
                )}
              />
            </Field>
          </div>

          <div className="pt-4 border-t border-[#e8dfd1]">
            <p className="text-xs tracking-[0.2em] uppercase text-[#8b6b4f] mb-1">Locked prompt (shown to logged-out visitors)</p>
            <p className="text-sm text-[#5a4a3d] mb-4">Clicking anywhere on this block opens the sign-up modal. Leave the entire block empty to hide it.</p>
            <div className="grid sm:grid-cols-2 gap-4">
              <Field label="Kicker"><TextInput value={data.vip.lockedKicker} onChange={(v) => update(['vip','lockedKicker'], v)} placeholder="Sign up to unlock" /></Field>
              <Field label="CTA label"><TextInput value={data.vip.lockedCtaLabel} onChange={(v) => update(['vip','lockedCtaLabel'], v)} placeholder="Join free" /></Field>
            </div>
            <Field label="Title"><TextInput value={data.vip.lockedTitle} onChange={(v) => update(['vip','lockedTitle'], v)} placeholder="Exclusive member perks" /></Field>
            <Field label="Body"><TextArea value={data.vip.lockedText} onChange={(v) => update(['vip','lockedText'], v)} rows={3} /></Field>
          </div>
        </SectionCard>
        )}

        {/* Footer */}
        {can('footer') && (
        <SectionCard title="Footer & Contact" open={openSections.footer} onToggle={() => toggle('footer')}>
          <div className="grid sm:grid-cols-2 gap-4">
            <Field label="Brand"><TextInput value={data.footer.brand} onChange={(v) => update(['footer','brand'], v)} /></Field>
            <Field label="Newsletter / contact email (shown in text)"><TextInput value={data.footer.email} onChange={(v) => update(['footer','email'], v)} /></Field>
          </div>
          <div className="grid sm:grid-cols-2 gap-4">
            <Field label="Email icon — recipient"><TextInput value={data.footer.contactEmail} onChange={(v) => update(['footer','contactEmail'], v)} placeholder="luca@essentialgemstones.com" /></Field>
            <Field label="Email icon — subject line"><TextInput value={data.footer.contactSubject} onChange={(v) => update(['footer','contactSubject'], v)} placeholder="Contact Essential Gemstones" /></Field>
          </div>
          <Field label="Tagline"><TextArea value={data.footer.tagline} onChange={(v) => update(['footer','tagline'], v)} rows={2} /></Field>
          <div className="grid sm:grid-cols-2 gap-4">
            <Field label="Newsletter kicker"><TextInput value={data.footer.newsletterKicker} onChange={(v) => update(['footer','newsletterKicker'], v)} /></Field>
            <Field label="Newsletter title"><TextInput value={data.footer.newsletterTitle} onChange={(v) => update(['footer','newsletterTitle'], v)} /></Field>
          </div>
          <div className="grid sm:grid-cols-2 gap-4">
            <Field label="Instagram URL"><TextInput value={data.footer.socials?.instagram} onChange={(v) => update(['footer','socials'], { ...data.footer.socials, instagram: v })} /></Field>
            <Field label="Facebook URL"><TextInput value={data.footer.socials?.facebook} onChange={(v) => update(['footer','socials'], { ...data.footer.socials, facebook: v })} /></Field>
          </div>
          <div className="grid sm:grid-cols-2 gap-4">
            <Field label="Donate title"><TextInput value={data.footer.donateTitle} onChange={(v) => update(['footer','donateTitle'], v)} /></Field>
            <Field label="Donate button label"><TextInput value={data.footer.donateLabel} onChange={(v) => update(['footer','donateLabel'], v)} /></Field>
          </div>
          <Field label="Donate text"><TextArea value={data.footer.donateText} onChange={(v) => update(['footer','donateText'], v)} rows={2} /></Field>
          <Field label="Donate URL"><TextInput value={data.footer.donateUrl} onChange={(v) => update(['footer','donateUrl'], v)} /></Field>
          <Field label="Copyright suffix"><TextInput value={data.footer.copyright} onChange={(v) => update(['footer','copyright'], v)} /></Field>
          <Field label="Closing quote"><TextInput value={data.footer.quote} onChange={(v) => update(['footer','quote'], v)} /></Field>
        </SectionCard>
        )}

        <div className="sticky bottom-4 z-30 flex justify-end">
          <button onClick={save} disabled={saving} className="inline-flex items-center gap-2 px-6 py-3 bg-[#1a1410] text-[#faf6f0] rounded-full text-sm shadow-2xl hover:bg-[#6b4f3a] disabled:opacity-60">
            {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Save all changes
          </button>
        </div>
      </main>
      <AIWriter open={aiOpen} onClose={() => setAiOpen(false)} />
    </div>
  );
}
