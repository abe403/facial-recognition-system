import { Component, ViewChild, ElementRef, OnInit, OnDestroy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService, Member } from '../../services/api.service';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="page-container animate-in">
      <header class="page-header">
        <h1>New Member</h1>
        <p>Register a member — their ID is auto-assigned after saving</p>
      </header>

      <div class="registration-grid">
        <!-- Step 1: Form -->
        <section class="glass-card form-section" [class.disabled]="step > 1">
          <h3>1. Basic Information</h3>
          <form #memberForm="ngForm" (ngSubmit)="submitMember()">
            <div class="form-group">
              <label>Full Name</label>
              <input type="text" [(ngModel)]="model.name" name="name" required placeholder="e.g. Abraham Torres">
            </div>

            <div class="form-group">
              <label>Expiration Date</label>
              <input type="date" [(ngModel)]="model.expiration_date" name="date" required>
            </div>

            <button type="submit" class="btn btn-primary w-full" [disabled]="!memberForm.valid || step > 1 || isSubmitting">
              {{ isSubmitting ? 'Saving...' : step === 1 ? 'Save & Continue' : 'Saved ✓' }}
            </button>
          </form>
        </section>

        <!-- Step 2: Facial Capture -->
        <section class="glass-card capture-section" [class.disabled]="step !== 2">
          <h3>2. Facial Capture</h3>

          <div *ngIf="createdMember" class="id-badge">
            <span class="id-label">Assigned ID</span>
            <span class="id-value">{{ createdMember.membership_id }}</span>
            <span class="id-num">#{{ createdMember.member_number }}</span>
          </div>

          <p class="step-desc">Position the member in front of the camera, centered in the guide circle</p>

          <div class="camera-wrapper">
            <div class="camera-container">
              <video #video autoplay playsinline></video>
              <div class="camera-overlay" *ngIf="isCameraActive">
                <div class="face-guide"></div>
              </div>
              <canvas #canvas style="display:none;"></canvas>
            </div>

            <div class="camera-controls">
              <button class="btn btn-primary" (click)="captureFace()" [disabled]="step !== 2 || isCapturing">
                {{ isCapturing ? 'Processing...' : 'Capture Face' }}
              </button>
              <p class="msg-text" *ngIf="message">{{ message }}</p>
            </div>
          </div>
        </section>
      </div>

      <!-- Final Success -->
      <div class="success-backdrop" *ngIf="step === 3" (click)="reset()">
        <div class="glass-card success-overlay" (click)="$event.stopPropagation()">
          <div class="success-icon">✨</div>
          <h2>Registration Complete</h2>
          <div class="success-id-block">
            <div class="success-id">{{ createdMember?.membership_id }}</div>
            <div class="success-num">Member #{{ createdMember?.member_number }}</div>
          </div>
          <p>{{ createdMember?.name }} is now registered with active facial biometrics.</p>
          <button class="btn btn-primary" (click)="reset()">Register Another</button>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .registration-grid {
      display: grid;
      grid-template-columns: 1fr 1.2fr;
      gap: 1.5rem;
    }

    h3 { margin-bottom: 1rem; }
    .step-desc { font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 1.5rem; }

    .disabled { opacity: 0.5; pointer-events: none; }

    .camera-wrapper { display: flex; flex-direction: column; gap: 1.5rem; }
    .camera-controls { text-align: center; }
    .w-full { width: 100%; }

    .id-badge {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.75rem 1rem;
      background: var(--accent-glow);
      border: 1px solid rgba(108, 92, 231, 0.3);
      border-radius: var(--radius-sm);
      margin-bottom: 1.25rem;
    }
    .id-label { font-size: 0.75rem; color: var(--text-secondary); text-transform: uppercase; }
    .id-value { font-family: monospace; font-size: 1.1rem; font-weight: 700; color: var(--accent); }
    .id-num { margin-left: auto; font-size: 0.8rem; color: var(--text-muted); }

    .success-backdrop {
      position: fixed; inset: 0;
      background: rgba(0,0,0,0.7);
      backdrop-filter: blur(6px);
      display: flex; align-items: center; justify-content: center;
      z-index: 200;
    }

    .success-overlay {
      text-align: center; width: 420px; padding: 2.5rem;
    }

    .success-icon { font-size: 4rem; margin-bottom: 1rem; }

    .success-id-block {
      margin: 1.5rem 0;
      padding: 1rem;
      background: var(--accent-glow);
      border-radius: var(--radius-sm);
    }
    .success-id { font-family: monospace; font-size: 1.5rem; font-weight: 700; color: var(--accent); }
    .success-num { font-size: 0.8rem; color: var(--text-secondary); margin-top: 0.25rem; }

    .msg-text { margin-top: 1rem; font-size: 0.85rem; color: var(--warning); }
  `]
})
export class RegisterComponent implements OnInit, OnDestroy {
  private api = inject(ApiService);

  @ViewChild('video') videoRef!: ElementRef<HTMLVideoElement>;
  @ViewChild('canvas') canvasRef!: ElementRef<HTMLCanvasElement>;

  step = 1;
  model = { name: '', expiration_date: this.getFutureDate() };
  createdMember?: Member;

  isCameraActive = false;
  isCapturing = false;
  isSubmitting = false;
  message = '';

  ngOnInit() {}
  ngOnDestroy() { this.stopCamera(); }

  getFutureDate() {
    const d = new Date();
    d.setFullYear(d.getFullYear() + 1);
    return d.toISOString().split('T')[0];
  }

  submitMember() {
    this.isSubmitting = true;
    this.api.registerMember(this.model).subscribe({
      next: (member) => {
        this.createdMember = member;
        this.step = 2;
        this.isSubmitting = false;
        this.startCamera();
      },
      error: (err) => {
        alert(err.error?.detail || 'Error saving member');
        this.isSubmitting = false;
      }
    });
  }

  async startCamera() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      this.videoRef.nativeElement.srcObject = stream;
      this.isCameraActive = true;
    } catch {
      alert('Could not access camera');
    }
  }

  captureFace() {
    if (!this.createdMember) return;
    this.isCapturing = true;
    this.message = '';

    const video = this.videoRef.nativeElement;
    const canvas = this.canvasRef.nativeElement;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d')?.drawImage(video, 0, 0);
    const b64 = canvas.toDataURL('image/jpeg', 0.9);

    this.api.uploadFace(this.createdMember.membership_id, b64).subscribe({
      next: () => {
        this.stopCamera();
        this.step = 3;
        this.isCapturing = false;
      },
      error: (err) => {
        this.message = err.error?.detail || 'Face not detected correctly. Try again.';
        this.isCapturing = false;
      }
    });
  }

  stopCamera() {
    const video = this.videoRef?.nativeElement;
    if (!video) return;
    const stream = video.srcObject as MediaStream;
    stream?.getTracks().forEach(t => t.stop());
    this.isCameraActive = false;
  }

  reset() {
    this.step = 1;
    this.model = { name: '', expiration_date: this.getFutureDate() };
    this.createdMember = undefined;
    this.message = '';
  }
}
