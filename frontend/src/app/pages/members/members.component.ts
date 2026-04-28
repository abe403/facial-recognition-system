import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService, Member } from '../../services/api.service';

@Component({
  selector: 'app-members',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="page-container animate-in">
      <header class="page-header">
        <div class="header-content">
          <div>
            <h1>Members</h1>
            <p>Manage gym memberships and facial samples</p>
          </div>
          <button class="btn btn-primary" (click)="refresh()">Refresh List</button>
        </div>
      </header>

      <section class="glass-card">
        <table class="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Membership ID</th>
              <th>Expiration</th>
              <th>Face Sample</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let member of members">
              <td class="name-cell">{{ member.name }}</td>
              <td class="id-cell">{{ member.membership_id }}</td>
              <td>
                <span [class]="isExpired(member.expiration_date) ? 'badge badge-expired' : 'badge badge-active'">
                  {{ member.expiration_date }}
                </span>
              </td>
              <td>
                <span *ngIf="member.has_face_sample" class="status-icon success">✓ Linked</span>
                <span *ngIf="!member.has_face_sample" class="status-icon danger">⚠ Missing</span>
              </td>
              <td>
                <div class="action-buttons">
                  <button class="icon-btn" title="Delete" (click)="delete(member)">🗑</button>
                </div>
              </td>
            </tr>
            <tr *ngIf="members.length === 0">
              <td colspan="5" class="empty-state">No members registered yet</td>
            </tr>
          </tbody>
        </table>
      </section>
    </div>
  `,
  styles: [`
    .header-content {
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
    }

    .name-cell {
      font-weight: 500;
      color: var(--text-primary);
    }

    .id-cell {
      font-family: monospace;
      color: var(--text-secondary);
    }

    .status-icon {
      font-size: 0.85rem;
      font-weight: 500;
    }

    .status-icon.success { color: var(--success); }
    .status-icon.danger { color: var(--danger); }

    .action-buttons {
      display: flex;
      gap: 0.5rem;
    }

    .icon-btn {
      background: transparent;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 4px 8px;
      color: var(--text-secondary);
      transition: var(--transition);
    }

    .icon-btn:hover {
      background: rgba(255, 107, 107, 0.1);
      color: var(--danger);
      border-color: var(--danger);
    }

    .empty-state {
      text-align: center;
      padding: 4rem;
      color: var(--text-muted);
    }
  `]
})
export class MembersComponent implements OnInit {
  private api = inject(ApiService);
  members: Member[] = [];

  ngOnInit() {
    this.refresh();
  }

  refresh() {
    this.api.getMembers().subscribe(m => this.members = m);
  }

  delete(member: Member) {
    if (confirm(`Are you sure you want to delete ${member.name}?`)) {
      this.api.deleteMember(member.membership_id).subscribe(() => this.refresh());
    }
  }

  isExpired(dateStr: string): boolean {
    const exp = new Date(dateStr);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return exp < today;
  }
}
