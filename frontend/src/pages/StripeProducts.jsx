import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, RefreshCw, Plus, Trash2, Package, Receipt, Ticket, Undo2, CheckCircle2, AlertTriangle, Pencil, X } from 'lucide-react';
import api, { resolveMediaUrl } from '../lib/api';
import { useToast } from '../hooks/use-toast';
import { Field, TextInput, TextArea } from '../components/admin/FormControls';
import MediaPicker from '../components/admin/MediaPicker';

const TABS = [
  { key: 'products', label: 'Products', icon: Package },
  { key: 'orders', label: 'Orders', icon: Receipt },
  { key: 'discounts', label: 'Discounts', icon: Ticket },
];

const money = (cents, cur = 'usd') => (cents == null ? '—' : `${(cents / 100).toFixed(2)} ${String(cur).toUpperCase()}`);

export default function StripeProducts() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [tab, setTab] = useState('products');
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!localStorage.getItem('eg_admin_token')) { navigate('/admin'); return; }
    api.get('/admin/stripe/status').then((r) => setStatus(r.data)).catch(() => setStatus({ configured: false })).finally(() => setLoading(false));
  }, [navigate]);

  if (loading) return <div className="min-h-screen flex items-center justify-center bg-[#faf6f0]"><RefreshCw className="w-6 h-6 animate-spin text-[#6b4f3a]" /></div>;

  return (
    <div className="min-h-screen bg-[#faf6f0]">
      <header className="sticky top-0 z-40 bg-[#1a1410] text-[#faf6f0] border-b border-[#3d2f24]">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Link to="/admin/dashboard" className="inline-flex items-center gap-2 px-3 py-2 text-sm border border-[#3d2f24] rounded-full hover:bg-[#241b15]"><ArrowLeft className="w-4 h-4" /> Dashboard</Link>
            <h1 className="font-serif text-xl">Stripe Store</h1>
          </div>
          {status?.configured ? (
            <span data-testid="stripe-status-badge" className="inline-flex items-center gap-1.5 text-xs bg-green-500/15 text-green-300 border border-green-500/30 px-3 py-1.5 rounded-full"><CheckCircle2 className="w-3.5 h-3.5" /> Connected · {status.mode}</span>
          ) : (
            <span data-testid="stripe-status-badge" className="inline-flex items-center gap-1.5 text-xs bg-amber-500/15 text-amber-300 border border-amber-500/30 px-3 py-1.5 rounded-full"><AlertTriangle className="w-3.5 h-3.5" /> Not connected</span>
          )}
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
        {!status?.configured ? (
          <NotConnected error={status?.error} />
        ) : (
          <>
            <div className="flex gap-2 mb-6 overflow-x-auto">
              {TABS.map((t) => {
                const Icon = t.icon;
                return (
                  <button key={t.key} data-testid={`stripe-tab-${t.key}`} onClick={() => setTab(t.key)}
                    className={`inline-flex items-center gap-2 px-4 py-2.5 rounded-full text-sm whitespace-nowrap transition-colors ${tab === t.key ? 'bg-[#1a1410] text-[#faf6f0]' : 'bg-white border border-[#e8dfd1] text-[#3d3128] hover:border-[#c9a876]'}`}>
                    <Icon className="w-4 h-4" /> {t.label}
                  </button>
                );
              })}
            </div>
            {tab === 'products' && <ProductsTab toast={toast} />}
            {tab === 'orders' && <OrdersTab toast={toast} />}
            {tab === 'discounts' && <DiscountsTab toast={toast} />}
          </>
        )}
      </main>
    </div>
  );
}

function NotConnected({ error }) {
  return (
    <div data-testid="stripe-not-connected" className="max-w-2xl mx-auto bg-white border border-[#e8dfd1] rounded-3xl p-8 text-center">
      <span className="w-14 h-14 rounded-full bg-[#f3ece0] flex items-center justify-center mx-auto mb-5"><Package className="w-7 h-7 text-[#6b4f3a]" /></span>
      <h2 className="font-serif text-3xl text-[#1a1410] mb-3">Connect your Stripe account</h2>
      <p className="text-sm text-[#5a4a3d] mb-5 leading-relaxed">To manage products, orders, refunds and discount codes here, add your Stripe <strong>Secret key</strong> to this app. Once it's set, this page turns on automatically.</p>
      <ol className="text-left text-sm text-[#3d3128] space-y-2 mb-6 max-w-md mx-auto">
        <li>1. In Stripe, go to <strong>Developers → API keys</strong> and copy your <strong>Secret key</strong> (starts with <code>sk_test_</code> or <code>sk_live_</code>).</li>
        <li>2. In Emergent, open the <strong>Payments / Secrets</strong> panel and add a secret named <code>STRIPE_API_KEY</code> with that value.</li>
        <li>3. Come back here and refresh — you'll see "Connected".</li>
      </ol>
      {error && <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-xl px-3 py-2">Last check: {error}</p>}
    </div>
  );
}

const emptyProduct = { name: '', description: '', price: '', images: [], active: true };

function ProductsTab({ toast }) {
  const [items, setItems] = useState(null);
  const [editing, setEditing] = useState(null); // product object or 'new'
  const [form, setForm] = useState(emptyProduct);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try { const { data } = await api.get('/admin/stripe/products'); setItems(data.products || []); }
    catch (e) { toast({ title: 'Could not load products', description: e?.response?.data?.detail || e.message, variant: 'destructive' }); setItems([]); }
  }, [toast]);
  useEffect(() => { load(); }, [load]);

  const startNew = () => { setForm(emptyProduct); setEditing('new'); };
  const startEdit = (p) => {
    setForm({ name: p.name || '', description: p.description || '', price: p.price?.unit_amount != null ? (p.price.unit_amount / 100).toFixed(2) : '', images: p.images || [], active: p.active });
    setEditing(p);
  };

  const save = async () => {
    if (!form.name.trim()) { toast({ title: 'Name required', variant: 'destructive' }); return; }
    setSaving(true);
    try {
      const body = { name: form.name, description: form.description, price: parseFloat(form.price || 0), images: form.images, active: form.active };
      if (editing === 'new') await api.post('/admin/stripe/products', body);
      else await api.put(`/admin/stripe/products/${editing.id}`, body);
      toast({ title: 'Saved to Stripe', description: form.name });
      setEditing(null); await load();
    } catch (e) { toast({ title: 'Save failed', description: e?.response?.data?.detail || e.message, variant: 'destructive' }); }
    finally { setSaving(false); }
  };

  const remove = async (p) => {
    if (!window.confirm(`Delete "${p.name}" from Stripe? (If it has past sales it will be archived instead.)`)) return;
    try { await api.delete(`/admin/stripe/products/${p.id}`); toast({ title: 'Removed', description: p.name }); load(); }
    catch (e) { toast({ title: 'Delete failed', description: e?.response?.data?.detail || e.message, variant: 'destructive' }); }
  };

  if (items === null) return <RefreshCw className="w-5 h-5 animate-spin text-[#6b4f3a] mx-auto" />;

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <p className="text-sm text-[#5a4a3d]">{items.length} product(s) in your Stripe catalog.</p>
        <button data-testid="stripe-add-product" onClick={startNew} className="inline-flex items-center gap-2 px-4 py-2.5 bg-[#1a1410] text-[#faf6f0] rounded-full text-sm hover:bg-[#6b4f3a]"><Plus className="w-4 h-4" /> Add product</button>
      </div>

      {editing && (
        <div className="bg-white border border-[#c9a876]/50 rounded-2xl p-5 mb-5" data-testid="stripe-product-form">
          <div className="flex justify-between items-center mb-4">
            <h3 className="font-serif text-lg text-[#1a1410]">{editing === 'new' ? 'New product' : `Edit: ${editing.name}`}</h3>
            <button onClick={() => setEditing(null)} className="w-8 h-8 rounded-full hover:bg-[#faf6f0] flex items-center justify-center"><X className="w-4 h-4" /></button>
          </div>
          <div className="grid sm:grid-cols-2 gap-4">
            <Field label="Name"><TextInput value={form.name} onChange={(v) => setForm({ ...form, name: v })} placeholder="Lava Stone Bracelet" /></Field>
            <Field label="Price (USD)"><TextInput value={form.price} onChange={(v) => setForm({ ...form, price: v })} placeholder="28.00" /></Field>
          </div>
          <Field label="Description"><TextArea value={form.description} onChange={(v) => setForm({ ...form, description: v })} rows={2} /></Field>
          <MediaPicker value={form.images?.[0] || ''} onChange={(url) => setForm({ ...form, images: url ? [url] : [] })} label="Product photo" accept="image/*" />
          <label className="flex items-center gap-2 mt-3 text-sm text-[#3d3128] cursor-pointer">
            <input type="checkbox" checked={form.active} onChange={(e) => setForm({ ...form, active: e.target.checked })} className="accent-[#6b4f3a]" data-testid="stripe-product-active" />
            Visible in the shop (active)
          </label>
          <button onClick={save} disabled={saving} data-testid="stripe-product-save" className="mt-4 inline-flex items-center gap-2 px-5 py-2.5 bg-[#c9a876] text-[#1a1410] rounded-full text-sm font-medium hover:bg-[#d6b885] disabled:opacity-60">
            {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />} Save to Stripe
          </button>
        </div>
      )}

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {items.map((p) => (
          <div key={p.id} data-testid={`stripe-product-${p.id}`} className="bg-white border border-[#e8dfd1] rounded-2xl overflow-hidden">
            <div className="aspect-[4/3] bg-[#e8dfd1]">{p.images?.[0] && <img src={resolveMediaUrl(p.images[0])} alt={p.name} className="w-full h-full object-cover" />}</div>
            <div className="p-4">
              <div className="flex items-start justify-between gap-2">
                <h4 className="font-serif text-lg text-[#1a1410] leading-tight">{p.name}</h4>
                {!p.active && <span className="text-[10px] uppercase tracking-wide bg-[#f3ece0] text-[#8b6b4f] px-2 py-0.5 rounded shrink-0">Hidden</span>}
              </div>
              <p className="text-[#6b4f3a] font-medium mt-1">{money(p.price?.unit_amount, p.price?.currency)}</p>
              <div className="flex gap-2 mt-3">
                <button onClick={() => startEdit(p)} className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 border border-[#e8dfd1] rounded-full text-sm hover:bg-[#faf6f0]"><Pencil className="w-3.5 h-3.5" /> Edit</button>
                <button onClick={() => remove(p)} aria-label="Delete" className="px-3 py-2 border border-[#e8dfd1] rounded-full text-red-700 hover:bg-red-50"><Trash2 className="w-3.5 h-3.5" /></button>
              </div>
            </div>
          </div>
        ))}
      </div>
      {items.length === 0 && !editing && <p className="text-center text-sm text-[#8b6b4f] italic py-10">No products yet. Click "Add product" to create your first one — it goes straight into Stripe.</p>}
    </div>
  );
}

function OrdersTab({ toast }) {
  const [orders, setOrders] = useState(null);
  const load = useCallback(async () => {
    try { const { data } = await api.get('/admin/stripe/payments'); setOrders(data.payments || []); }
    catch (e) { toast({ title: 'Could not load orders', description: e?.response?.data?.detail || e.message, variant: 'destructive' }); setOrders([]); }
  }, [toast]);
  useEffect(() => { load(); }, [load]);

  const refund = async (o) => {
    if (!o.payment_intent) { toast({ title: 'No payment to refund', variant: 'destructive' }); return; }
    if (!window.confirm(`Refund ${money(o.amount, o.currency)} to ${o.customer_email || 'the customer'}?`)) return;
    try { await api.post('/admin/stripe/refund', { payment_intent: o.payment_intent }); toast({ title: 'Refund issued' }); load(); }
    catch (e) { toast({ title: 'Refund failed', description: e?.response?.data?.detail || e.message, variant: 'destructive' }); }
  };

  if (orders === null) return <RefreshCw className="w-5 h-5 animate-spin text-[#6b4f3a] mx-auto" />;
  if (orders.length === 0) return <p className="text-center text-sm text-[#8b6b4f] italic py-10">No orders yet. Completed checkouts will appear here.</p>;

  return (
    <div className="bg-white border border-[#e8dfd1] rounded-2xl divide-y divide-[#e8dfd1]" data-testid="stripe-orders-list">
      {orders.map((o) => (
        <div key={o.id} className="p-4 flex items-center justify-between gap-3 flex-wrap">
          <div className="min-w-0">
            <p className="text-sm text-[#1a1410] font-medium">{money(o.amount, o.currency)} {o.refunded && <span className="text-xs text-red-700">· refunded</span>}</p>
            <p className="text-xs text-[#8b6b4f] truncate">{o.customer_email || 'guest'} · {o.payment_status} · {o.created ? new Date(o.created * 1000).toLocaleString() : ''}</p>
          </div>
          {o.payment_status === 'paid' && !o.refunded && (
            <button onClick={() => refund(o)} className="inline-flex items-center gap-1.5 px-3 py-2 border border-[#e8dfd1] rounded-full text-sm text-red-700 hover:bg-red-50"><Undo2 className="w-3.5 h-3.5" /> Refund</button>
          )}
        </div>
      ))}
    </div>
  );
}

function DiscountsTab({ toast }) {
  const [coupons, setCoupons] = useState(null);
  const [form, setForm] = useState({ name: '', kind: 'percent', value: '', code: '', duration: 'once' });
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try { const { data } = await api.get('/admin/stripe/coupons'); setCoupons(data.coupons || []); }
    catch (e) { toast({ title: 'Could not load discounts', description: e?.response?.data?.detail || e.message, variant: 'destructive' }); setCoupons([]); }
  }, [toast]);
  useEffect(() => { load(); }, [load]);

  const create = async () => {
    if (!form.name.trim() || !form.value) { toast({ title: 'Name and value required', variant: 'destructive' }); return; }
    setSaving(true);
    try {
      const body = { name: form.name, duration: form.duration, code: form.code || undefined };
      if (form.kind === 'percent') body.percent_off = parseFloat(form.value);
      else body.amount_off = parseFloat(form.value);
      await api.post('/admin/stripe/coupons', body);
      toast({ title: 'Discount created' });
      setForm({ name: '', kind: 'percent', value: '', code: '', duration: 'once' });
      load();
    } catch (e) { toast({ title: 'Create failed', description: e?.response?.data?.detail || e.message, variant: 'destructive' }); }
    finally { setSaving(false); }
  };

  const remove = async (c) => {
    if (!window.confirm(`Delete discount "${c.code}"?`)) return;
    try { await api.delete(`/admin/stripe/coupons/${c.coupon_id}`); toast({ title: 'Deleted' }); load(); }
    catch (e) { toast({ title: 'Delete failed', description: e?.response?.data?.detail || e.message, variant: 'destructive' }); }
  };

  return (
    <div className="grid lg:grid-cols-2 gap-6">
      <div className="bg-white border border-[#e8dfd1] rounded-2xl p-5" data-testid="stripe-coupon-form">
        <h3 className="font-serif text-lg text-[#1a1410] mb-4">Create a discount code</h3>
        <Field label="Internal name"><TextInput value={form.name} onChange={(v) => setForm({ ...form, name: v })} placeholder="Family discount" /></Field>
        <Field label="Code customers type (optional)"><TextInput value={form.code} onChange={(v) => setForm({ ...form, code: v })} placeholder="FAMILY10" /></Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Type">
            <div className="flex gap-2">
              {['percent', 'amount'].map((k) => (
                <button key={k} type="button" onClick={() => setForm({ ...form, kind: k })} className={`flex-1 px-3 py-2 rounded-full text-sm border ${form.kind === k ? 'bg-[#1a1410] text-[#faf6f0] border-[#1a1410]' : 'border-[#e8dfd1] hover:bg-[#faf6f0]'}`}>{k === 'percent' ? '% off' : '$ off'}</button>
              ))}
            </div>
          </Field>
          <Field label={form.kind === 'percent' ? 'Percent (e.g. 10)' : 'Amount USD (e.g. 5)'}><TextInput value={form.value} onChange={(v) => setForm({ ...form, value: v })} placeholder={form.kind === 'percent' ? '10' : '5.00'} /></Field>
        </div>
        <button onClick={create} disabled={saving} data-testid="stripe-coupon-save" className="mt-2 inline-flex items-center gap-2 px-5 py-2.5 bg-[#c9a876] text-[#1a1410] rounded-full text-sm font-medium hover:bg-[#d6b885] disabled:opacity-60">
          {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />} Create discount
        </button>
        <p className="text-[11px] text-[#8b6b4f] mt-3">Customers enter the code at checkout to get the discount.</p>
      </div>

      <div>
        <h3 className="font-serif text-lg text-[#1a1410] mb-4">Active codes</h3>
        {coupons === null ? <RefreshCw className="w-5 h-5 animate-spin text-[#6b4f3a]" /> : coupons.length === 0 ? (
          <p className="text-sm text-[#8b6b4f] italic">No discount codes yet.</p>
        ) : (
          <div className="bg-white border border-[#e8dfd1] rounded-2xl divide-y divide-[#e8dfd1]" data-testid="stripe-coupons-list">
            {coupons.map((c) => (
              <div key={c.id} className="p-4 flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-mono text-[#1a1410]">{c.code}</p>
                  <p className="text-xs text-[#8b6b4f]">{c.percent_off ? `${c.percent_off}% off` : `${money(c.amount_off, c.currency)} off`} · {c.duration} · used {c.times_redeemed || 0}×</p>
                </div>
                <button onClick={() => remove(c)} aria-label="Delete" className="px-3 py-2 border border-[#e8dfd1] rounded-full text-red-700 hover:bg-red-50"><Trash2 className="w-3.5 h-3.5" /></button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
