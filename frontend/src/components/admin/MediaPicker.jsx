import React, { useRef, useState } from 'react';
import { Upload, Image as ImageIcon, X, Loader2 } from 'lucide-react';
import api, { resolveMediaUrl } from '../../lib/api';
import { useToast } from '../../hooks/use-toast';

export default function MediaPicker({ value, onChange, accept = 'image/*,video/*', label = 'Media' }) {
  const inputRef = useRef(null);
  const [uploading, setUploading] = useState(false);
  const { toast } = useToast();

  const handleFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const form = new FormData();
      form.append('file', file);
      const { data } = await api.post('/upload', form, { headers: { 'Content-Type': 'multipart/form-data' } });
      onChange(data.url, data.kind);
      toast({ title: 'Uploaded', description: `${data.kind} uploaded successfully.` });
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Upload failed';
      toast({ title: 'Upload failed', description: String(msg), variant: 'destructive' });
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  };

  const display = resolveMediaUrl(value);
  const isVideo = value && /\.(mp4|mov|webm|m4v)$/i.test(value);

  return (
    <div>
      <label className="block text-xs tracking-[0.2em] uppercase text-[#8b6b4f] mb-2">{label}</label>
      <div className="flex flex-col sm:flex-row gap-3 items-start">
        <div className="w-32 h-24 rounded-xl overflow-hidden border border-[#e8dfd1] bg-[#f3ece0] flex items-center justify-center shrink-0">
          {value ? (isVideo ? <video src={display} className="w-full h-full object-cover" muted /> : <img src={display} alt="" className="w-full h-full object-cover" />) : <ImageIcon className="w-6 h-6 text-[#8b6b4f]" />}
        </div>
        <div className="flex-1 w-full">
          <input value={value || ''} onChange={(e) => onChange(e.target.value)} className="w-full px-4 py-2.5 border border-[#e8dfd1] rounded-lg focus:border-[#6b4f3a] focus:outline-none text-sm mb-2" placeholder="https://... or /api/uploads/..." />
          <div className="flex items-center gap-2">
            <button type="button" onClick={() => inputRef.current?.click()} disabled={uploading} className="inline-flex items-center gap-2 px-3 py-2 text-xs bg-[#1a1410] text-[#faf6f0] rounded-lg hover:bg-[#6b4f3a] transition-colors disabled:opacity-60">
              {uploading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Upload className="w-3 h-3" />} {uploading ? 'Uploading\u2026' : 'Upload'}
            </button>
            {value && (
              <button type="button" onClick={() => onChange('')} className="inline-flex items-center gap-1 px-3 py-2 text-xs border border-[#e8dfd1] rounded-lg hover:bg-[#f3ece0]"><X className="w-3 h-3" /> Clear</button>
            )}
          </div>
          <input ref={inputRef} type="file" accept={accept} onChange={handleFile} className="hidden" />
        </div>
      </div>
    </div>
  );
}
