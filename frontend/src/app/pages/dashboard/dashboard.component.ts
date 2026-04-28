import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService, Stats, AttendanceRecord } from '../../services/api.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="page-container animate-in">
      <header class="page-header">
        <h1>Dashboard</h1>
        <p>Real-time analytics and system overview</p>
      </header>

      <div class="stats-grid" *ngIf="stats">
        <div class="glass-card stat-card">
          <div class="stat-value">{{ stats.total_members }}</div>
          <div class="stat-label">Total Members</div>
        </div>
        <div class="glass-card stat-card">
          <div class="stat-value">{{ stats.active_members }}</div>
          <div class="stat-label">Active Plans</div>
        </div>
        <div class="glass-card stat-card">
          <div class="stat-value">{{ stats.entries_today }}</div>
          <div class="stat-label">Entries Today</div>
        </div>
        <div class="glass-card stat-card">
          <div class="stat-value">{{ stats.entries_this_week }}</div>
          <div class="stat-label">This Week</div>
        </div>
      </div>

      <div class="main-grid">
        <section class="glass-card table-section">
          <div class="section-header">
            <h3>Recent Activity</h3>
            <button class="btn btn-outline btn-sm" (click)="loadData()">Refresh</button>
          </div>
          
          <table class="data-table">
            <thead>
              <tr>
                <th>Member</th>
                <th>ID</th>
                <th>Date</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let entry of attendance">
                <td>{{ entry.name }}</td>
                <td class="id-cell">{{ entry.membership_id }}</td>
                <td>{{ entry.date }}</td>
                <td>{{ entry.time }}</td>
              </tr>
              <tr *ngIf="attendance.length === 0">
                <td colspan="4" class="empty-state">No recent activity found</td>
              </tr>
            </tbody>
          </table>
        </section>

        <section class="glass-card status-section">
          <h3>System Integrity</h3>
          <div class="status-list">
            <div class="status-item">
              <span class="dot online"></span>
              <div class="status-info">
                <div class="status-label">FastAPI Backend</div>
                <div class="status-desc">Connected • v2.0.0</div>
              </div>
            </div>
            <div class="status-item">
              <span class="dot online"></span>
              <div class="status-info">
                <div class="status-label">LBPH Recognizer</div>
                <div class="status-desc">Model Trained • {{ stats?.total_members || 0 }} samples</div>
              </div>
            </div>
            <div class="status-item">
              <span class="dot online"></span>
              <div class="status-info">
                <div class="status-label">Database</div>
                <div class="status-desc">SQLite Connected</div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  `,
  styles: [`
    .main-grid {
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 1.5rem;
    }

    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.5rem;
    }

    h3 {
      font-size: 1.1rem;
      font-weight: 600;
    }

    .id-cell {
      font-family: monospace;
      color: var(--text-secondary);
    }

    .empty-state {
      text-align: center;
      padding: 3rem;
      color: var(--text-muted);
      font-style: italic;
    }

    .status-list {
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
      margin-top: 1.5rem;
    }

    .status-item {
      display: flex;
      gap: 1rem;
      align-items: flex-start;
    }

    .status-info {
      flex: 1;
    }

    .status-label {
      font-size: 0.9rem;
      font-weight: 500;
      margin-bottom: 0.1rem;
    }

    .status-desc {
      font-size: 0.75rem;
      color: var(--text-secondary);
    }

    .dot.online {
      margin-top: 0.4rem;
      width: 8px;
      height: 8px;
      background: var(--success);
      border-radius: 50%;
      box-shadow: 0 0 10px var(--success-glow);
    }

    .btn-sm {
      padding: 0.4rem 0.8rem;
      font-size: 0.8rem;
    }
  `]
})
export class DashboardComponent implements OnInit {
  private api = inject(ApiService);
  stats?: Stats;
  attendance: AttendanceRecord[] = [];

  ngOnInit() {
    this.loadData();
  }

  loadData() {
    this.api.getStats().subscribe(s => this.stats = s);
    this.api.getAttendance().subscribe(a => this.attendance = a);
  }
}
