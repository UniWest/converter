/*
 Resilient chunked uploader with:
 - 413 handling: halve chunk size, rewind to last confirmed offset, exponential backoff
 - Up to N concurrent chunk uploads
 - Persist state in localStorage: upload_id, next_offset, chunk_size
 - Optional pre-compress images above configurable megapixels

 Framework-agnostic TypeScript. Works with fetch API.
*/

export type UploaderEvents = {
  onProgress?: (bytesUploaded: number, total: number) => void;
  onChunkSuccess?: (rangeStart: number, rangeEnd: number) => void;
  onChunkError?: (err: any) => void;
  onState?: (state: PersistedState) => void;
};

export type CompressionConfig = {
  enabled: boolean;
  maxMegapixels: number; // if image megapixels > this, downscale
  outputType?: 'image/jpeg' | 'image/webp' | 'image/png';
  quality?: number; // 0..1
};

export type UploaderConfig = {
  endpoint: string; // upload endpoint
  method?: string; // default: 'PUT' for chunks
  initEndpoint?: string; // optional endpoint to init upload and get upload_id
  initMethod?: string; // default: 'POST'
  headers?: Record<string, string>; // extra headers
  initialChunkSize?: number; // default 1 MiB
  minChunkSize?: number; // default 64 KiB
  maxConcurrency?: number; // default 3
  backoffBaseMs?: number; // default 500ms
  backoffMaxMs?: number; // default 15000ms
  storageKeyPrefix?: string; // default 'resumable_upload:'
  uploadId?: string; // optionally provide existing upload id
  compression?: CompressionConfig; // optional image pre-compression
  // Header names customization
  headerNames?: {
    contentRange?: string; // default 'Content-Range'
    uploadId?: string; // default 'Upload-Id'
    contentType?: string; // default 'Content-Type'
  };
};

export type PersistedState = {
  upload_id: string;
  next_offset: number;
  chunk_size: number;
  file_name: string;
  file_size: number;
  file_type: string;
};

function sleep(ms: number) {
  return new Promise((res) => setTimeout(res, ms));
}

function clamp(n: number, min: number, max: number) {
  return Math.max(min, Math.min(max, n));
}

function isImageType(mime: string) {
  return /^image\//.test(mime);
}

async function readFileAsImageBitmap(file: Blob): Promise<ImageBitmap> {
  // Prefer createImageBitmap where available
  if (typeof createImageBitmap === 'function') {
    return await createImageBitmap(file);
  }
  // Fallback via HTMLImageElement
  const url = URL.createObjectURL(file);
  try {
    const img = await new Promise<HTMLImageElement>((resolve, reject) => {
      const i = new Image();
      i.onload = () => resolve(i);
      i.onerror = reject;
      i.src = url;
    });
    // @ts-ignore - OffscreenCanvas types may not be available in all TS targets
    const bitmap = await (self as any).createImageBitmap?.(img);
    if (bitmap) return bitmap as ImageBitmap;
    // As a last resort, draw and return canvas image data dimensions via custom object
    // but we require a bitmap-like object; throw to use canvas path below.
    throw new Error('createImageBitmap not supported');
  } finally {
    URL.revokeObjectURL(url);
  }
}

async function downscaleImageIfNeeded(
  file: File,
  cfg: CompressionConfig
): Promise<File> {
  if (!cfg.enabled || !isImageType(file.type)) return file;
  try {
    const bmp = await readFileAsImageBitmap(file).catch(() => null);
    if (!bmp) {
      // Fallback path: draw via <img> onto canvas
      // We'll attempt canvas draw using HTMLImageElement
      const dataUrl = await new Promise<string>((resolve, reject) => {
        const url = URL.createObjectURL(file);
        const img = new Image();
        img.onload = () => {
          // @ts-ignore
          const c = document.createElement('canvas');
          c.width = img.width;
          c.height = img.height;
          const ctx = c.getContext('2d');
          if (!ctx) return reject(new Error('No 2D context'));
          ctx.drawImage(img, 0, 0);
          c.toBlob(
            (blob) => {
              URL.revokeObjectURL(url);
              if (!blob) return reject(new Error('Canvas toBlob failed'));
              const f = new File([blob], file.name, { type: blob.type });
              resolve(URL.createObjectURL(f));
            },
            cfg.outputType || 'image/jpeg',
            clamp(cfg.quality ?? 0.85, 0.1, 1)
          );
        };
        img.onerror = (e) => {
          URL.revokeObjectURL(url);
          reject(e);
        };
        img.src = url;
      });
      // We cannot easily get megapixels here; skip downscale on this rare path.
      URL.revokeObjectURL(dataUrl);
      return file;
    }
    const w = bmp.width;
    const h = bmp.height;
    const mp = (w * h) / 1_000_000;
    if (mp <= cfg.maxMegapixels) return file;

    const scale = Math.sqrt(cfg.maxMegapixels / mp);
    const targetW = Math.max(1, Math.floor(w * scale));
    const targetH = Math.max(1, Math.floor(h * scale));

    // Use canvas to draw downscaled image
    const canvas = document.createElement('canvas');
    canvas.width = targetW;
    canvas.height = targetH;
    const ctx = canvas.getContext('2d');
    if (!ctx) return file;
    // Use high quality scaling where available
    (ctx as any).imageSmoothingEnabled = true;
    (ctx as any).imageSmoothingQuality = 'high';
    // @ts-ignore drawImage accepts ImageBitmap
    ctx.drawImage(bmp, 0, 0, targetW, targetH);

    const mime = cfg.outputType || (file.type === 'image/png' ? 'image/png' : 'image/jpeg');
    const quality = clamp(cfg.quality ?? (mime === 'image/jpeg' ? 0.85 : 0.92), 0.1, 1);

    const blob: Blob = await new Promise((resolve, reject) => {
      canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('toBlob failed'))), mime, quality);
    });

    const newFile = new File([blob], file.name, { type: mime, lastModified: file.lastModified });
    return newFile;
  } catch {
    return file; // fail-open if compression fails
  }
}

export class ResilientUploader {
  private cfg: UploaderConfig;
  private file: File;
  private uploadId: string;
  private chunkSize: number;
  private minChunkSize: number;
  private nextOffset: number = 0;
  private confirmedOffset: number = 0;
  private maxConcurrency: number;
  private backoffBaseMs: number;
  private backoffMaxMs: number;
  private storageKey: string;
  private restartRequested = false;
  private controllers: AbortController[] = [];
  private events: UploaderEvents;

  constructor(file: File, cfg: UploaderConfig, events: UploaderEvents = {}) {
    this.file = file;
    this.cfg = cfg;
    this.events = events;
    this.chunkSize = Math.max(64 * 1024, cfg.initialChunkSize ?? 1 * 1024 * 1024);
    this.minChunkSize = Math.max(16 * 1024, cfg.minChunkSize ?? 64 * 1024);
    this.maxConcurrency = clamp(cfg.maxConcurrency ?? 3, 1, 8);
    this.backoffBaseMs = cfg.backoffBaseMs ?? 500;
    this.backoffMaxMs = cfg.backoffMaxMs ?? 15000;
    const prefix = cfg.storageKeyPrefix ?? 'resumable_upload:';
    // Storage key based on file identity and endpoint
    this.storageKey = `${prefix}${cfg.endpoint}|${file.name}|${file.size}|${file.type}`;
    this.uploadId = cfg.uploadId || this.restoreState()?.upload_id || self.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`;

    const restored = this.restoreState();
    if (restored) {
      this.nextOffset = restored.next_offset;
      this.confirmedOffset = restored.next_offset;
      this.chunkSize = restored.chunk_size;
    }
  }

  private restoreState(): PersistedState | null {
    try {
      const raw = localStorage.getItem(this.storageKey);
      if (!raw) return null;
      const st = JSON.parse(raw) as PersistedState;
      if (st.file_size !== this.file.size || st.file_name !== this.file.name) return null;
      return st;
    } catch {
      return null;
    }
  }

  private persistState() {
    const state: PersistedState = {
      upload_id: this.uploadId,
      next_offset: this.nextOffset,
      chunk_size: this.chunkSize,
      file_name: this.file.name,
      file_size: this.file.size,
      file_type: this.file.type,
    };
    try {
      localStorage.setItem(this.storageKey, JSON.stringify(state));
      this.events.onState?.(state);
    } catch {}
  }

  private clearState() {
    try {
      localStorage.removeItem(this.storageKey);
    } catch {}
  }

  private makeContentRange(start: number, endInclusive: number, total: number) {
    const headerName = this.cfg.headerNames?.contentRange || 'Content-Range';
    const value = `bytes ${start}-${endInclusive}/${total}`;
    return { name: headerName, value };
  }

  private getUploadIdHeader() {
    const name = this.cfg.headerNames?.uploadId || 'Upload-Id';
    return { name, value: this.uploadId };
  }

  private makeHeaders(contentType?: string): Headers {
    const h = new Headers();
    const ctName = this.cfg.headerNames?.contentType || 'Content-Type';
    if (contentType) h.set(ctName, contentType);
    const uid = this.getUploadIdHeader();
    h.set(uid.name, uid.value);
    if (this.cfg.headers) {
      for (const [k, v] of Object.entries(this.cfg.headers)) h.set(k, v);
    }
    return h;
  }

  private computeBackoff(attempt: number) {
    const base = this.backoffBaseMs;
    const cap = this.backoffMaxMs;
    const jitter = Math.random() * 0.25 + 0.75; // 0.75x..1x
    return Math.min(cap, Math.round(base * Math.pow(2, attempt) * jitter));
  }

  private resetControllers() {
    for (const c of this.controllers) try { c.abort(); } catch {}
    this.controllers = [];
  }

  private claimChunk(): { start: number; end: number } | null {
    if (this.restartRequested) return null;
    if (this.nextOffset >= this.file.size) return null;
    const start = this.nextOffset;
    const end = Math.min(this.file.size, start + this.chunkSize) - 1; // inclusive
    this.nextOffset = end + 1;
    this.persistState();
    return { start, end };
  }

  private confirmChunk(endInclusive: number) {
    if (endInclusive + 1 > this.confirmedOffset) {
      this.confirmedOffset = endInclusive + 1;
      this.events.onProgress?.(this.confirmedOffset, this.file.size);
      this.persistState();
    }
  }

  private async sendChunk(start: number, end: number, attempt = 0): Promise<Response> {
    const blob = this.file.slice(start, end + 1);
    const headers = this.makeHeaders(this.file.type);
    const cr = this.makeContentRange(start, end, this.file.size);
    headers.set(cr.name, cr.value);

    const ctrl = new AbortController();
    this.controllers.push(ctrl);

    try {
      const res = await fetch(this.cfg.endpoint, {
        method: this.cfg.method || 'PUT',
        headers,
        body: blob,
        signal: ctrl.signal,
      });
      return res;
    } finally {
      // remove controller
      this.controllers = this.controllers.filter((c) => c !== ctrl);
    }
  }

  private async handle413AndRestart() {
    this.restartRequested = true;
    // abort inflight
    this.resetControllers();
    // halve chunk size with floor and clamp to min
    this.chunkSize = clamp(Math.floor(this.chunkSize / 2), this.minChunkSize, this.chunkSize);
    // rewind to last confirmed
    this.nextOffset = this.confirmedOffset;
    this.persistState();
  }

  async start(): Promise<string> {
    // Optional: init upload to get uploadId from server
    if (this.cfg.initEndpoint) {
      const initRes = await fetch(this.cfg.initEndpoint, {
        method: this.cfg.initMethod || 'POST',
        headers: this.makeHeaders('application/json'),
        body: JSON.stringify({ fileName: this.file.name, fileSize: this.file.size, fileType: this.file.type, uploadId: this.uploadId }),
      });
      if (!initRes.ok) throw new Error(`Init upload failed: ${initRes.status}`);
      try {
        const data = await initRes.json();
        if (data?.upload_id) this.uploadId = String(data.upload_id);
      } catch {}
    }

    // Optional compression
    if (this.cfg.compression?.enabled) {
      const newFile = await downscaleImageIfNeeded(this.file, this.cfg.compression);
      this.file = newFile;
    }

    let attempt = 0;

    while (this.confirmedOffset < this.file.size) {
      this.restartRequested = false;

      // Launch up to maxConcurrency workers
      const worker = async () => {
        for (;;) {
          if (this.restartRequested) return;
          const claim = this.claimChunk();
          if (!claim) return;
          const { start, end } = claim;
          try {
            const res = await this.sendChunk(start, end);
            if (res.status === 413) {
              // Too large for proxy/buffer
              await this.handle413AndRestart();
              throw new Error('RESTART_413');
            }
            if (!res.ok) {
              // Other error: retry with backoff
              throw new Error(`HTTP_${res.status}`);
            }
            this.confirmChunk(end);
            this.events.onChunkSuccess?.(start, end);
            attempt = 0; // reset global backoff after success
          } catch (err: any) {
            if (String(err?.message).includes('RESTART_413')) {
              // bubble up to outer loop to restart workers
              throw err;
            }
            this.events.onChunkError?.(err);
            // transient error backoff
            const delay = this.computeBackoff(attempt++);
            await sleep(delay);
            // rewind this specific chunk by setting nextOffset back if needed
            // but because we may have other claims, we rely on restart cycle or worker loop to re-claim remaining bytes
            // Retry this same chunk immediately
            // Ensure we haven't restarted in the meantime
            if (!this.restartRequested) {
              // Re-send the same chunk
              try {
                const res2 = await this.sendChunk(start, end);
                if (res2.status === 413) {
                  await this.handle413AndRestart();
                  throw new Error('RESTART_413');
                }
                if (!res2.ok) throw new Error(`HTTP_${res2.status}`);
                this.confirmChunk(end);
                this.events.onChunkSuccess?.(start, end);
                attempt = 0;
              } catch (err2: any) {
                if (String(err2?.message).includes('RESTART_413')) throw err2;
                // Give up this chunk for now; outer loop/backoff handles
                // Put pointer back so it can be re-claimed next cycle
                if (start < this.nextOffset) {
                  this.nextOffset = Math.min(this.nextOffset, start);
                  this.persistState();
                }
                return;
              }
            } else {
              return;
            }
          }
        }
      };

      const workers = Array.from({ length: this.maxConcurrency }, () => worker());

      try {
        await Promise.all(workers);
      } catch (e: any) {
        // A 413 triggered restart
        if (String(e?.message).includes('RESTART_413')) {
          // exponential backoff before restart
          const delay = this.computeBackoff(attempt++);
          await sleep(delay);
          continue; // restart while loop
        }
        // Other error: backoff and continue
        const delay = this.computeBackoff(attempt++);
        await sleep(delay);
        continue;
      }

      // If we get here without restart and without confirming all bytes, loop continues
    }

    this.clearState();
    return this.uploadId;
  }
}

export default ResilientUploader;

