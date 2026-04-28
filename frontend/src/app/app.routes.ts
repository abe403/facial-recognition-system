import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
  {
    path: 'dashboard',
    loadComponent: () =>
      import('./pages/dashboard/dashboard.component').then(m => m.DashboardComponent),
  },
  {
    path: 'register',
    loadComponent: () =>
      import('./pages/register/register.component').then(m => m.RegisterComponent),
  },
  {
    path: 'verify',
    loadComponent: () =>
      import('./pages/verify/verify.component').then(m => m.VerifyComponent),
  },
  {
    path: 'members',
    loadComponent: () =>
      import('./pages/members/members.component').then(m => m.MembersComponent),
  },
  {
    path: 'kiosk',
    loadComponent: () =>
      import('./pages/kiosk/kiosk.component').then(m => m.KioskComponent),
  },
  { path: '**', redirectTo: 'dashboard' },
];
