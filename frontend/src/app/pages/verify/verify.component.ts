import { Component, ViewChild, ElementRef, OnInit, OnDestroy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ApiService, RecognitionResult } from '../../services/api.service';

@Component({
  selector: 'app-verify',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="page-container animate-in">
      <header class="page-header">
        <h1>Access Control</h1>
        <p>Biometric identity verification</p>
      </header>

      <div class="verification-layout">
        <!-- Camera Section -->
        <div class="glass-card camera-panel">
          <div class="camera-wrapper">
            <div class="camera-container">
              <video #video autoplay playsinline></video>
              <div class="camera-overlay">
                <div class="face-guide"></div>
              </div>
              <canvas #canvas style="display:none;"></canvas>
            </div>
          </div>
          
          <div class="controls">
            <button class="btn btn-primary" (click)="verify()" [disabled]="isVerifying">
              {{ isVerifying ? 'Verifying...' : 'Verify Identity' }}
            </button>
          </div>
        </div>

        <!-- Result Section -->
        <div class="result-panel-wrapper">
          <div *ngIf="!result && !isVerifying" class="glass-card empty-result">
            <div class="icon">👤</div>
            <p>Awaiting verification...</p>
          </div>

          <div *ngIf="isVerifying" class="glass-card verifying-state">
            <div class="spinner"></div>
            <p>Analyzing biometrics...</p>
          </div>

          <!-- Success / Granted -->
          <div *ngIf="result?.recognized && result?.access_granted" class="result-panel result-granted">
            <div class="result-icon">✓</div>
            <h2>Access Granted</h2>
            <div class="member-info">
              <div class="m-name">{{ result?.name }}</div>
              <div class="m-id">ID: {{ result?.membership_id }}</div>
            </div>
            <p class="status-msg">{{ result?.message }}</p>
          </div>

          <!-- Denied / Expired -->
          <div *ngIf="result?.recognized && !result?.access_granted" class="result-panel result-denied">
            <div class="result-icon">✕</div>
            <h2>Access Denied</h2>
            <div class="member-info">
              <div class="m-name">{{ result?.name }}</div>
              <div class="m-id">ID: {{ result?.membership_id }}</div>
            </div>
            <p class="status-msg">{{ result?.message }}</p>
          </div>

          <!-- Not Recognized or No Members -->
          <div *ngIf="result && !result.recognized" class="result-panel result-unknown">
            <div class="result-icon">?</div>
            <h2>{{ result.message.includes('No members') ? 'System Empty' : 'Unknown Face' }}</h2>
            <p class="status-msg">{{ result.message }}</p>
            <button *ngIf="result.message.includes('No members')" 
                    class="btn btn-primary btn-sm" 
                    style="margin-top: 1rem"
                    routerLink="/register">
              Go to Registration
            </button>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .verification-layout {
      display: grid;
      grid-template-columns: 1.2fr 1fr;
      gap: 2rem;
      align-items: start;
    }

    .camera-panel {
      padding: 2rem;
    }

    .controls {
      margin-top: 2rem;
      text-align: center;
    }

    .result-panel-wrapper {
      height: 100%;
    }

    .empty-result, .verifying-state {
      height: 400px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 1rem;
      color: var(--text-secondary);
    }

    .empty-result .icon { font-size: 3rem; opacity: 0.3; }

    .member-info {
      margin: 1.5rem 0;
      padding: 1rem;
      background: rgba(255,255,255,0.05);
      border-radius: var(--radius-sm);
    }

    .m-name { font-size: 1.4rem; font-weight: 700; }
    .m-id { font-family: monospace; color: var(--text-secondary); margin-top: 0.25rem; }

    .status-msg { font-size: 0.95rem; line-height: 1.5; margin-top: 1rem; color: var(--text-secondary); }

    .spinner {
      width: 40px;
      height: 40px;
      border: 3px solid var(--border);
      border-top-color: var(--accent);
      border-radius: 50%;
      animation: spin 1s linear infinite;
    }

    @keyframes spin { to { transform: rotate(360deg); } }
  `]
})
export class VerifyComponent implements OnInit, OnDestroy {
  private api = inject(ApiService);

  @ViewChild('video') videoRef!: ElementRef<HTMLVideoElement>;
  @ViewChild('canvas') canvasRef!: ElementRef<HTMLCanvasElement>;

  isVerifying = false;
  result?: RecognitionResult;

  ngOnInit() {
    this.startCamera();
  }

  ngOnDestroy() {
    this.stopCamera();
  }

  async startCamera() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      this.videoRef.nativeElement.srcObject = stream;
    } catch (err) {
      alert('Could not access camera');
    }
  }

  stopCamera() {
    const stream = this.videoRef.nativeElement.srcObject as MediaStream;
    stream?.getTracks().forEach(t => t.stop());
  }

  verify() {
    this.isVerifying = true;
    this.result = undefined;

    const video = this.videoRef.nativeElement;
    const canvas = this.canvasRef.nativeElement;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    const ctx = canvas.getContext('2d');
    ctx?.drawImage(video, 0, 0);
    
    const b64 = canvas.toDataURL('image/png');

    this.api.recognize(b64).subscribe({
      next: (res) => {
        this.result = res;
        this.isVerifying = false;
      },
      error: (err) => {
        alert('Server error during verification');
        this.isVerifying = false;
      }
    });
  }
}
