import { Component, OnInit, inject } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive, Router, NavigationEnd } from '@angular/router';
import { CommonModule } from '@angular/common';
import { filter } from 'rxjs/operators';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, CommonModule],
  template: `
    <!-- ── KIOSK LAYOUT: Full screen, no shell ── -->
    <ng-container *ngIf="isKiosk">
      <router-outlet></router-outlet>
    </ng-container>

    <!-- ── DASHBOARD LAYOUT: Sidebar + content ── -->
    <ng-container *ngIf="!isKiosk">
      <nav class="sidebar">
        <div class="logo">
          <span class="logo-icon">🏋️</span>
          <span class="logo-text">FaceGym</span>
        </div>

        <div class="nav-links">
          <a routerLink="/dashboard" routerLinkActive="active" class="nav-item">
            <span class="icon">📊</span>
            <span>Dashboard</span>
          </a>
          <a routerLink="/verify" routerLinkActive="active" class="nav-item">
            <span class="icon">🔍</span>
            <span>Access Control</span>
          </a>
          <a routerLink="/members" routerLinkActive="active" class="nav-item">
            <span class="icon">👥</span>
            <span>Members</span>
          </a>
          <a routerLink="/register" routerLinkActive="active" class="nav-item">
            <span class="icon">➕</span>
            <span>New Member</span>
          </a>

          <div class="nav-divider"></div>

          <a routerLink="/kiosk" class="nav-item kiosk-link" target="_blank" rel="noopener">
            <span class="icon">🖥️</span>
            <span>Open Kiosk</span>
            <span class="external-badge">↗</span>
          </a>
        </div>

        <div class="sidebar-footer">
          <div class="status-indicator">
            <span class="dot"></span>
            <span>System Online</span>
          </div>
        </div>
      </nav>

      <main class="content-area">
        <router-outlet></router-outlet>
      </main>
    </ng-container>
  `,
  styles: [`
    /* Shared host */
    :host {
      display: flex;
      height: 100vh;
      overflow: hidden;
    }

    /* ── Kiosk full-screen ───────────────────────── */
    ng-container:first-child {
      display: contents;
    }

    /* ── Sidebar ─────────────────────────────────── */
    .sidebar {
      width: 260px;
      background: var(--bg-secondary);
      border-right: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      padding: 2rem 1.5rem;
      flex-shrink: 0;
    }

    .logo {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      margin-bottom: 3rem;
      padding-left: 0.5rem;
    }

    .logo-icon { font-size: 1.5rem; }
    .logo-text { font-size: 1.25rem; font-weight: 700; letter-spacing: -0.02em; }

    .nav-links {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      flex: 1;
    }

    .nav-item {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.75rem 1rem;
      text-decoration: none;
      color: var(--text-secondary);
      border-radius: var(--radius-sm);
      transition: var(--transition);
      font-size: 0.95rem;
      font-weight: 500;
      border: 1px solid transparent;
    }

    .nav-item:hover {
      background: rgba(255, 255, 255, 0.05);
      color: var(--text-primary);
    }

    .nav-item.active {
      background: var(--accent-glow);
      color: var(--accent);
      border-color: rgba(108, 92, 231, 0.2);
    }

    .icon {
      font-size: 1.1rem;
      width: 24px;
      display: flex;
      justify-content: center;
    }

    .nav-divider {
      height: 1px;
      background: var(--border);
      margin: 0.5rem 0;
    }

    .kiosk-link {
      color: var(--success) !important;
      opacity: 0.7;
    }

    .kiosk-link:hover {
      opacity: 1;
      background: rgba(0, 206, 201, 0.08) !important;
    }

    .external-badge {
      margin-left: auto;
      font-size: 0.8rem;
      opacity: 0.6;
    }

    .content-area {
      flex: 1;
      overflow-y: auto;
      background: var(--bg-primary);
    }

    .sidebar-footer {
      margin-top: auto;
      padding-top: 2rem;
    }

    .status-indicator {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.75rem;
      color: var(--text-muted);
      padding-left: 0.5rem;
    }

    .dot {
      width: 8px;
      height: 8px;
      background: var(--success);
      border-radius: 50%;
      box-shadow: 0 0 10px var(--success-glow);
    }
  `]
})
export class AppComponent implements OnInit {
  private router = inject(Router);
  isKiosk = false;

  ngOnInit() {
    this.router.events
      .pipe(filter(e => e instanceof NavigationEnd))
      .subscribe((e: NavigationEnd) => {
        this.isKiosk = e.urlAfterRedirects.startsWith('/kiosk');
      });

    // Check initial URL (e.g. direct browser navigation to /kiosk)
    this.isKiosk = this.router.url.startsWith('/kiosk');
  }
}
