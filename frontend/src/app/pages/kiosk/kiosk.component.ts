import {
  Component, ViewChild, ElementRef,
  OnInit, OnDestroy, inject, NgZone
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService, RecognitionResult } from '../../services/api.service';

type KioskState = 'idle' | 'scanning' | 'granted' | 'denied' | 'expired' | 'unknown';

const SCAN_INTERVAL_MS = 2500;  // How often to auto-scan when idle
const RESULT_HOLD_MS = 6000;    // How long to show a result before resetting

@Component({
  selector: 'app-kiosk',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="kiosk-root" [attr.data-state]="state">

      <!-- ── Header ── -->
      <header class="kiosk-header">
        <div class="gym-brand">
          <span class="brand-icon">🏋️</span>
          <span class="brand-name">FaceGym</span>
        </div>
        <div class="kiosk-clock">{{ currentTime }}</div>
      </header>

      <!-- ── Main: centered camera ── -->
      <main class="kiosk-main">

        <div class="camera-stage">

          <!-- Video feed -->
          <video #video autoplay playsinline muted></video>
          <canvas #canvas style="display:none;"></canvas>

          <!-- Face guide -->
          <div class="face-guide-layer">
            <div class="face-oval" [class.pulse]="state === 'idle' || state === 'scanning'">
              <div class="corner tl"></div>
              <div class="corner tr"></div>
              <div class="corner bl"></div>
              <div class="corner br"></div>
            </div>
            <div class="scan-line" *ngIf="state === 'scanning'"></div>
          </div>

          <!-- Idle hint -->
          <div class="idle-hint" *ngIf="state === 'idle'">
            <span class="pulse-dot"></span> Stand here to be verified automatically
          </div>

          <!-- Scanning hint -->
          <div class="scanning-hint" *ngIf="state === 'scanning'">
            <div class="scan-spinner"></div>
            Analyzing biometrics…
          </div>

          <!-- ── Result overlay (slides up from bottom of camera) ── -->
          <div class="result-overlay"
               *ngIf="state !== 'idle' && state !== 'scanning'"
               [class.overlay-granted]="state === 'granted'"
               [class.overlay-denied]="state === 'denied' || state === 'expired'"
               [class.overlay-unknown]="state === 'unknown'">

            <!-- ACCESS GRANTED -->
            <ng-container *ngIf="state === 'granted'">
              <div class="result-icon-badge granted-badge">✓</div>
              <div class="result-headline">ACCESS GRANTED</div>
              <div class="result-name">{{ result?.name }}</div>
              <div class="result-sub">
                <span class="id-chip">{{ result?.membership_id }}</span>
                <span class="expiry-chip">
                  Membership expires {{ formatDate(result?.expiration_date) }}
                </span>
              </div>
            </ng-container>

            <!-- EXPIRED -->
            <ng-container *ngIf="state === 'expired'">
              <div class="result-icon-badge denied-badge">✕</div>
              <div class="result-headline">MEMBERSHIP EXPIRED</div>
              <div class="result-name">{{ result?.name }}</div>
              <div class="result-sub">
                <span class="id-chip">{{ result?.membership_id }}</span>
                <span class="expiry-chip expired-chip">
                  Expired {{ formatDate(result?.expiration_date) }}
                </span>
              </div>
              <div class="result-help">Please contact staff to renew</div>
            </ng-container>

            <!-- NOT RECOGNIZED -->
            <ng-container *ngIf="state === 'denied'">
              <div class="result-icon-badge denied-badge">?</div>
              <div class="result-headline">NOT RECOGNIZED</div>
              <div class="result-help">Please contact staff for assistance</div>
            </ng-container>

            <!-- SYSTEM ERROR / EMPTY -->
            <ng-container *ngIf="state === 'unknown'">
              <div class="result-icon-badge warn-badge">!</div>
              <div class="result-headline">UNABLE TO SCAN</div>
              <div class="result-help">{{ result?.message }}</div>
            </ng-container>

          </div><!-- /result-overlay -->

          <!-- Camera border glow (state-driven) -->
          <div class="stage-glow"></div>
        </div>

        <!-- Manual fallback button -->
        <button class="scan-btn"
                (click)="triggerManualScan()"
                [disabled]="state === 'scanning'"
                [class.is-scanning]="state === 'scanning'">
          <span class="scan-dot"></span>
          {{ state === 'scanning' ? 'Scanning…' : 'Scan Now' }}
        </button>

      </main>

      <!-- ── Footer ── -->
      <footer class="kiosk-footer">
        Powered by FaceGym v2 · Biometric Access Control
      </footer>

    </div>
  `,
  styles: [`
    /* ── Host ───────────────────────────────────────────────────────── */
    :host {
      display: block;
    }

    /* ── Root ───────────────────────────────────────────────────────── */
    .kiosk-root {
      position: fixed;
      inset: 0;
      z-index: 1000;
      display: flex;
      flex-direction: column;
      background: var(--bg-primary);
      overflow: hidden;
      transition: background 0.6s ease;
    }

    .kiosk-root[data-state="granted"] { background: #071510; }
    .kiosk-root[data-state="denied"],
    .kiosk-root[data-state="expired"]  { background: #150707; }
    .kiosk-root[data-state="unknown"]  { background: #141007; }

    /* ── Header ──────────────────────────────────────────────────────── */
    .kiosk-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1.1rem 2.5rem;
      border-bottom: 1px solid var(--border);
      background: var(--bg-secondary);
      flex-shrink: 0;
    }

    .gym-brand {
      display: flex; align-items: center; gap: 0.75rem;
      font-size: 1.35rem; font-weight: 700;
    }
    .brand-icon { font-size: 1.5rem; }

    .kiosk-clock {
      font-size: 1.25rem;
      font-weight: 600;
      font-variant-numeric: tabular-nums;
      color: var(--text-secondary);
    }

    /* ── Main ────────────────────────────────────────────────────────── */
    .kiosk-main {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 1.75rem;
      padding: 1.5rem;
      overflow: hidden;
    }

    /* ── Camera stage ────────────────────────────────────────────────── */
    .camera-stage {
      position: relative;
      /* Fill most of the vertical space, keep 16:9 ish, centered */
      width: min(75vh, 90vw);
      aspect-ratio: 4 / 3;
      border-radius: 28px;
      overflow: hidden;
      background: #000;
      box-shadow: 0 0 80px rgba(0,0,0,0.6);
      border: 2px solid rgba(255,255,255,0.06);
      transition: border-color 0.4s ease, box-shadow 0.5s ease;
    }

    /* State-driven glow via the pseudo-element overlay */
    .kiosk-root[data-state="granted"]  .camera-stage {
      border-color: rgba(0,206,201,0.4);
      box-shadow: 0 0 80px rgba(0,206,201,0.25), 0 0 160px rgba(0,206,201,0.1);
    }
    .kiosk-root[data-state="denied"] .camera-stage,
    .kiosk-root[data-state="expired"] .camera-stage {
      border-color: rgba(255,107,107,0.4);
      box-shadow: 0 0 80px rgba(255,107,107,0.25), 0 0 160px rgba(255,107,107,0.1);
    }
    .kiosk-root[data-state="scanning"] .camera-stage {
      border-color: rgba(108,92,231,0.5);
      box-shadow: 0 0 80px rgba(108,92,231,0.3);
    }

    video {
      width: 100%; height: 100%;
      object-fit: cover;
      transform: scaleX(-1);
      display: block;
    }

    /* ── Face guide ──────────────────────────────────────────────────── */
    .face-guide-layer {
      position: absolute; inset: 0;
      display: flex; align-items: center; justify-content: center;
      pointer-events: none;
    }

    .face-oval {
      width: 240px;
      height: 310px;
      border: 3px solid rgba(108,92,231,0.55);
      border-radius: 50%;
      position: relative;
      transition: border-color 0.4s;
    }

    .kiosk-root[data-state="granted"]  .face-oval { border-color: rgba(0,206,201,0.7); }
    .kiosk-root[data-state="denied"]   .face-oval,
    .kiosk-root[data-state="expired"]  .face-oval { border-color: rgba(255,107,107,0.7); }

    .face-oval.pulse { animation: ovalPulse 2.5s ease-in-out infinite; }

    @keyframes ovalPulse {
      0%, 100% { border-color: rgba(108,92,231,0.3); }
      50% {
        border-color: rgba(108,92,231,0.9);
        filter: drop-shadow(0 0 12px rgba(108,92,231,0.5));
      }
    }

    .corner {
      position: absolute;
      width: 22px; height: 22px;
      border-color: var(--accent);
      border-style: solid;
    }
    .corner.tl { top:-3px;left:-3px; border-width:3px 0 0 3px; border-radius:4px 0 0 0; }
    .corner.tr { top:-3px;right:-3px; border-width:3px 3px 0 0; border-radius:0 4px 0 0; }
    .corner.bl { bottom:-3px;left:-3px; border-width:0 0 3px 3px; border-radius:0 0 0 4px; }
    .corner.br { bottom:-3px;right:-3px; border-width:0 3px 3px 0; border-radius:0 0 4px 0; }

    .scan-line {
      position: absolute;
      left: -10%; width: 120%; height: 2px;
      background: linear-gradient(90deg, transparent, var(--accent), transparent);
      animation: scanDown 1.5s ease-in-out infinite;
      box-shadow: 0 0 12px var(--accent);
    }
    @keyframes scanDown {
      0%   { top: 8%; }
      50%  { top: 92%; }
      100% { top: 8%; }
    }

    /* ── Idle / Scanning hints ────────────────────────────────────────── */
    .idle-hint, .scanning-hint {
      position: absolute;
      bottom: 1.25rem;
      left: 50%;
      transform: translateX(-50%);
      background: rgba(0,0,0,0.65);
      backdrop-filter: blur(10px);
      padding: 0.55rem 1.4rem;
      border-radius: 999px;
      font-size: 0.9rem;
      color: var(--text-secondary);
      white-space: nowrap;
      display: flex; align-items: center; gap: 0.6rem;
    }

    .pulse-dot {
      display: inline-block;
      width: 8px; height: 8px;
      background: var(--accent);
      border-radius: 50%;
      animation: blinkDot 1.2s ease-in-out infinite;
      flex-shrink: 0;
    }

    .scan-spinner {
      width: 16px; height: 16px;
      border: 2px solid rgba(108,92,231,0.3);
      border-top-color: var(--accent);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    /* ── Result overlay ──────────────────────────────────────────────── */
    .result-overlay {
      position: absolute;
      bottom: 0; left: 0; right: 0;
      padding: 1.75rem 2rem 1.5rem;
      text-align: center;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.6rem;
      animation: slideUp 0.45s cubic-bezier(0.34, 1.56, 0.64, 1);
    }

    @keyframes slideUp {
      from { opacity: 0; transform: translateY(30px); }
      to   { opacity: 1; transform: translateY(0); }
    }

    .overlay-granted {
      background: linear-gradient(to top, rgba(0,206,201,0.9) 0%, rgba(0,206,201,0.75) 60%, transparent 100%);
    }
    .overlay-denied {
      background: linear-gradient(to top, rgba(255,107,107,0.9) 0%, rgba(255,107,107,0.75) 60%, transparent 100%);
    }
    .overlay-unknown {
      background: linear-gradient(to top, rgba(254,202,87,0.9) 0%, rgba(254,202,87,0.75) 60%, transparent 100%);
    }

    .result-icon-badge {
      font-size: 2rem;
      font-weight: 900;
      width: 60px; height: 60px;
      border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      animation: badgePop 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
    }
    @keyframes badgePop {
      from { transform: scale(0); }
      to   { transform: scale(1); }
    }

    .granted-badge { background: rgba(0,0,0,0.2); color: white; }
    .denied-badge  { background: rgba(0,0,0,0.2); color: white; }
    .warn-badge    { background: rgba(0,0,0,0.2); color: #0a0a0f; }

    .result-headline {
      font-size: 1rem;
      font-weight: 800;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: rgba(255,255,255,0.9);
    }

    .result-name {
      font-size: 2rem;
      font-weight: 700;
      color: white;
      text-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }

    .result-sub {
      display: flex;
      gap: 0.6rem;
      flex-wrap: wrap;
      justify-content: center;
    }

    .id-chip, .expiry-chip {
      padding: 0.3rem 0.85rem;
      border-radius: 999px;
      font-size: 0.82rem;
      font-weight: 600;
      background: rgba(0,0,0,0.2);
      color: rgba(255,255,255,0.9);
    }

    .expired-chip {
      background: rgba(0,0,0,0.3);
      color: rgba(255,200,200,0.95);
    }

    .result-help {
      font-size: 0.85rem;
      color: rgba(255,255,255,0.75);
      margin-top: 0.2rem;
    }

    /* ── Scan button ─────────────────────────────────────────────────── */
    .scan-btn {
      display: flex;
      align-items: center;
      gap: 0.85rem;
      padding: 1.1rem 3rem;
      background: var(--accent);
      color: white;
      border: none;
      border-radius: 999px;
      font-size: 1.15rem;
      font-weight: 700;
      cursor: pointer;
      letter-spacing: 0.01em;
      box-shadow: 0 8px 40px var(--accent-glow);
      transition: all 0.25s ease;
      flex-shrink: 0;
    }

    .scan-btn:hover:not(:disabled) {
      transform: translateY(-3px);
      box-shadow: 0 14px 50px var(--accent-glow);
    }

    .scan-btn:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }

    .scan-dot {
      width: 12px; height: 12px;
      border-radius: 50%;
      background: white;
    }

    .scan-btn.is-scanning .scan-dot {
      animation: blinkDot 0.8s ease-in-out infinite;
    }

    @keyframes blinkDot {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.2; }
    }

    /* ── Footer ──────────────────────────────────────────────────────── */
    .kiosk-footer {
      text-align: center;
      padding: 0.65rem;
      font-size: 0.72rem;
      color: var(--text-muted);
      border-top: 1px solid var(--border);
      flex-shrink: 0;
    }
  `]
})
export class KioskComponent implements OnInit, OnDestroy {
  private api = inject(ApiService);
  private zone = inject(NgZone);

  @ViewChild('video') videoRef!: ElementRef<HTMLVideoElement>;
  @ViewChild('canvas') canvasRef!: ElementRef<HTMLCanvasElement>;

  state: KioskState = 'idle';
  result?: RecognitionResult;
  currentTime = '';

  private clockInterval?: ReturnType<typeof setInterval>;
  private scanInterval?: ReturnType<typeof setInterval>;
  private resetTimer?: ReturnType<typeof setTimeout>;
  private isAutoScanning = false;

  ngOnInit() {
    this.startCamera();
    this.startClock();
    this.startAutoScan();
  }

  ngOnDestroy() {
    this.stopCamera();
    clearInterval(this.clockInterval);
    clearInterval(this.scanInterval);
    clearTimeout(this.resetTimer);
  }

  async startCamera() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' }
      });
      this.videoRef.nativeElement.srcObject = stream;
    } catch {
      console.error('Camera access denied');
    }
  }

  stopCamera() {
    const stream = this.videoRef?.nativeElement?.srcObject as MediaStream;
    stream?.getTracks().forEach(t => t.stop());
  }

  startClock() {
    const tick = () => {
      this.zone.run(() => {
        this.currentTime = new Date().toLocaleTimeString('es-MX', {
          hour: '2-digit', minute: '2-digit', second: '2-digit'
        });
      });
    };
    tick();
    this.clockInterval = setInterval(tick, 1000);
  }

  startAutoScan() {
    this.scanInterval = setInterval(() => {
      if (this.state === 'idle' && !this.isAutoScanning) {
        this.scan(false);
      }
    }, SCAN_INTERVAL_MS);
  }

  triggerManualScan() {
    clearInterval(this.scanInterval);
    this.scan(false);
    // Restart auto-scan after manual trigger
    this.startAutoScan();
  }

  scan(showScanningState = true) {
    clearTimeout(this.resetTimer);
    if (showScanningState) {
      this.state = 'scanning';
    }
    this.isAutoScanning = true;
    this.result = undefined;

    const video = this.videoRef.nativeElement;
    const canvas = this.canvasRef.nativeElement;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d')?.drawImage(video, 0, 0);
    const b64 = canvas.toDataURL('image/jpeg', 0.85);

    this.api.recognize(b64).subscribe({
      next: (res) => {
        this.zone.run(() => {
          // Silently ignore 'no face detected' — stay idle and keep scanning
          if (!res.recognized && res.message.toLowerCase().includes('no face')) {
            this.isAutoScanning = false;
            this.state = 'idle';
            return;
          }

          this.result = res;
          this.resolveState(res);
          this.isAutoScanning = false;

          this.resetTimer = setTimeout(() => {
            this.zone.run(() => { this.state = 'idle'; this.result = undefined; });
          }, RESULT_HOLD_MS);
        });
      },
      error: () => {
        this.zone.run(() => {
          this.isAutoScanning = false;
          // Don't show a result for network errors during auto-scan — just go idle
          this.state = 'idle';
        });
      }
    });
  }

  private resolveState(res: RecognitionResult) {
    if (!res.recognized) {
      this.state = res.message.includes('No members') ? 'unknown' : 'denied';
    } else if (res.access_granted) {
      this.state = 'granted';
    } else {
      this.state = 'expired';
    }
  }

  formatDate(dateStr?: string): string {
    if (!dateStr) return '';
    const [y, m, d] = dateStr.split('-');
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return `${months[parseInt(m) - 1]} ${d}, ${y}`;
  }
}
