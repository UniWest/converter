/*
 Resilient chunked uploader (ES module, no TypeScript) with:
 - 413 handling: halve chunk size, rewind to last confirmed offset, exponential backoff
 - Up to N concurrent chunk uploads
 - Persist state in localStorage: upload_id, next_offset, chunk_size
 - Optional pre-compress images above configurable megapixels
*/

function sleep(ms){ return new Promise(r=>setTimeout(r, ms)); }
function clamp(n, min, max){ return Math.max(min, Math.min(max, n)); }
function isImageType(mime){ return /^image\//.test(mime); }

async function readFileAsImageBitmap(file){
  if (typeof createImageBitmap === 'function') return await createImageBitmap(file);
  const url = URL.createObjectURL(file);
  try {
    const img = await new Promise((resolve, reject)=>{ const i=new Image(); i.onload=()=>resolve(i); i.onerror=reject; i.src=url; });
    const b = self.createImageBitmap?.(img);
    if (b) return await b;
    throw new Error('createImageBitmap not supported');
  } finally { URL.revokeObjectURL(url); }
}

async function downscaleImageIfNeeded(file, cfg){
  if (!cfg?.enabled || !isImageType(file.type)) return file;
  try {
    const bmp = await readFileAsImageBitmap(file).catch(()=>null);
    if (!bmp) return file; // fallback path skipped for simplicity
    const w = bmp.width, h = bmp.height;
    const mp = (w*h)/1_000_000;
    if (mp <= cfg.maxMegapixels) return file;
    const scale = Math.sqrt(cfg.maxMegapixels / mp);
    const targetW = Math.max(1, Math.floor(w*scale));
    const targetH = Math.max(1, Math.floor(h*scale));
    const canvas = document.createElement('canvas');
    canvas.width = targetW; canvas.height = targetH;
    const ctx = canvas.getContext('2d'); if (!ctx) return file;
    ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = 'high';
    ctx.drawImage(bmp, 0, 0, targetW, targetH);
    const mime = cfg.outputType || (file.type === 'image/png' ? 'image/png' : 'image/jpeg');
    const quality = clamp(cfg.quality ?? (mime==='image/jpeg'?0.85:0.92), 0.1, 1);
    const blob = await new Promise((res, rej)=>canvas.toBlob(b=>b?res(b):rej(new Error('toBlob failed')), mime, quality));
    return new File([blob], file.name, { type: mime, lastModified: file.lastModified });
  } catch { return file; }
}

export class ResilientUploader {
  constructor(file, cfg={}, events={}){
    this.file = file;
    this.cfg = cfg;
    this.events = events;
    this.chunkSize = Math.max(64*1024, cfg.initialChunkSize ?? 1*1024*1024);
    this.minChunkSize = Math.max(16*1024, cfg.minChunkSize ?? 64*1024);
    this.maxConcurrency = clamp(cfg.maxConcurrency ?? 3, 1, 8);
    this.backoffBaseMs = cfg.backoffBaseMs ?? 500;
    this.backoffMaxMs = cfg.backoffMaxMs ?? 15000;
    const prefix = cfg.storageKeyPrefix ?? 'resumable_upload:';
    this.storageKey = `${prefix}${cfg.endpoint}|${file.name}|${file.size}|${file.type}`;
    const restored = this._restoreState();
    this.uploadId = cfg.uploadId || restored?.upload_id || (self.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`);
    this.nextOffset = restored?.next_offset || 0;
    this.confirmedOffset = restored?.next_offset || 0;
    this.chunkSize = restored?.chunk_size || this.chunkSize;
    this.restartRequested = false;
    this.controllers = [];
  }
  _restoreState(){ try{ const raw=localStorage.getItem(this.storageKey); if(!raw) return null; const st=JSON.parse(raw); if(st.file_size!==this.file.size||st.file_name!==this.file.name) return null; return st; }catch{ return null; } }
  _persistState(){ const st={ upload_id:this.uploadId, next_offset:this.nextOffset, chunk_size:this.chunkSize, file_name:this.file.name, file_size:this.file.size, file_type:this.file.type }; try{ localStorage.setItem(this.storageKey, JSON.stringify(st)); this.events.onState?.(st);}catch{} }
  _clearState(){ try{ localStorage.removeItem(this.storageKey);}catch{} }
  _makeContentRange(start, endInc, total){ const name=this.cfg.headerNames?.contentRange||'Content-Range'; return { name, value:`bytes ${start}-${endInc}/${total}`}; }
  _getUploadIdHeader(){ const name=this.cfg.headerNames?.uploadId||'Upload-Id'; return { name, value: this.uploadId }; }
  _makeHeaders(contentType){ const h=new Headers(); const ctName=this.cfg.headerNames?.contentType||'Content-Type'; if(contentType) h.set(ctName, contentType); const uid=this._getUploadIdHeader(); h.set(uid.name, uid.value); if(this.cfg.headers) for (const [k,v] of Object.entries(this.cfg.headers)) h.set(k,v); return h; }
  _computeBackoff(attempt){ const base=this.backoffBaseMs, cap=this.backoffMaxMs; const jitter=Math.random()*0.25+0.75; return Math.min(cap, Math.round(base*Math.pow(2, attempt)*jitter)); }
  _resetControllers(){ for(const c of this.controllers) try{c.abort()}catch{} this.controllers=[]; }
  _claimChunk(){ if(this.restartRequested) return null; if(this.nextOffset>=this.file.size) return null; const start=this.nextOffset; const end=Math.min(this.file.size, start+this.chunkSize)-1; this.nextOffset=end+1; this._persistState(); return {start,end}; }
  _confirmChunk(endInc){ if(endInc+1>this.confirmedOffset){ this.confirmedOffset=endInc+1; this.events.onProgress?.(this.confirmedOffset, this.file.size); this._persistState(); } }
  async _sendChunk(start, end){ const blob=this.file.slice(start, end+1); const headers=this._makeHeaders(this.file.type); const cr=this._makeContentRange(start, end, this.file.size); headers.set(cr.name, cr.value); const ctrl=new AbortController(); this.controllers.push(ctrl); try{ const res=await fetch(this.cfg.endpoint, { method:this.cfg.method||'PUT', headers, body:blob, signal:ctrl.signal }); return res; } finally { this.controllers=this.controllers.filter(c=>c!==ctrl); } }
  async _handle413AndRestart(){ this.restartRequested=true; this._resetControllers(); this.chunkSize = clamp(Math.floor(this.chunkSize/2), this.minChunkSize, this.chunkSize); this.nextOffset=this.confirmedOffset; this._persistState(); }

  async start(){
    if (this.cfg.initEndpoint){
      const initRes = await fetch(this.cfg.initEndpoint, { method:this.cfg.initMethod||'POST', headers:this._makeHeaders('application/json'), body: JSON.stringify({ fileName:this.file.name, fileSize:this.file.size, fileType:this.file.type, uploadId:this.uploadId }) });
      if(!initRes.ok) throw new Error(`Init upload failed: ${initRes.status}`);
      try{ const data=await initRes.json(); if(data?.upload_id) this.uploadId=String(data.upload_id); }catch{}
    }
    if (this.cfg.compression?.enabled){ this.file = await downscaleImageIfNeeded(this.file, this.cfg.compression); }

    let attempt = 0;
    while (this.confirmedOffset < this.file.size){
      this.restartRequested=false;
      const worker = async ()=>{
        for(;;){ if(this.restartRequested) return; const claim=this._claimChunk(); if(!claim) return; const {start,end}=claim; try{ const res=await this._sendChunk(start,end); if(res.status===413){ await this._handle413AndRestart(); throw new Error('RESTART_413'); } if(!res.ok) throw new Error(`HTTP_${res.status}`); this._confirmChunk(end); this.events.onChunkSuccess?.(start,end); attempt=0; } catch(err){ if(String(err?.message).includes('RESTART_413')) throw err; this.events.onChunkError?.(err); const delay=this._computeBackoff(attempt++); await sleep(delay); if(!this.restartRequested){ try{ const res2=await this._sendChunk(start,end); if(res2.status===413){ await this._handle413AndRestart(); throw new Error('RESTART_413'); } if(!res2.ok) throw new Error(`HTTP_${res2.status}`); this._confirmChunk(end); this.events.onChunkSuccess?.(start,end); attempt=0; } catch(err2){ if(String(err2?.message).includes('RESTART_413')) throw err2; if(start < this.nextOffset){ this.nextOffset = Math.min(this.nextOffset, start); this._persistState(); } return; } } else { return; } }
        }
      };
      const workers = Array.from({length:this.maxConcurrency}, ()=>worker());
      try { await Promise.all(workers); } catch(e){ if(String(e?.message).includes('RESTART_413')){ const d=this._computeBackoff(attempt++); await sleep(d); continue; } const d=this._computeBackoff(attempt++); await sleep(d); continue; }
    }
    this._clearState();
    return this.uploadId;
  }
}

export default ResilientUploader;

