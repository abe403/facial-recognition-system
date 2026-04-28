import { Routes } from '@angular/router';
import { authGuard } from './core/auth/auth.guard';

export const routes: Routes = [
  { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
  {
    path: 'login',
    loadComponent: () =>
      import('./pages/login/login.component').then(m => m.LoginComponent),
  },
  {
    path: 'dashboard',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./pages/dashboard/dashboard.component').then(m => m.DashboardComponent),
  },
  {
    path: 'register',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./pages/register/register.component').then(m => m.RegisterComponent),
  },
  {
    path: 'verify',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./pages/verify/verify.component').then(m => m.VerifyComponent),
  },
  {
    path: 'members',
    canActivate: [authGuard],
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
