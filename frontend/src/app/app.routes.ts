import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () => import('./features/landing/landing.component').then(c => c.LandingComponent),
    pathMatch: 'full',
  },
  {
    path: 'login',
    loadComponent: () => import('./features/login/login.component').then(c => c.LoginComponent),
  },
  {
    path: 'simulations',
    canActivate: [authGuard],
    loadComponent: () => import('./features/simulation-list/simulation-list.component').then(c => c.SimulationListComponent),
  },
  {
    path: 'simulations/create',
    canActivate: [authGuard],
    loadComponent: () => import('./features/simulation-create/simulation-create.component').then(c => c.SimulationCreateComponent),
  },
  {
    path: 'settings',
    canActivate: [authGuard],
    loadComponent: () => import('./features/settings/settings.component').then(c => c.SettingsComponent),
  },
  {
    path: 'simulation/:id',
    canActivate: [authGuard],
    loadComponent: () => import('./features/simulation-dashboard/simulation-dashboard.component').then(c => c.SimulationDashboardComponent),
    children: [
      { path: '', redirectTo: 'overview', pathMatch: 'full' },

      // Flache Tabs
      { path: 'overview',  loadComponent: () => import('./features/simulation-dashboard/overview/overview.component').then(c => c.OverviewComponent) },
      { path: 'personas',  loadComponent: () => import('./features/simulation-dashboard/personas/personas.component').then(c => c.PersonasComponent) },
      { path: 'network',   loadComponent: () => import('./features/simulation-dashboard/network/network.component').then(c => c.NetworkComponent) },
      { path: 'sentiment', loadComponent: () => import('./features/simulation-dashboard/sentiment/sentiment.component').then(c => c.SentimentComponent) },
      { path: 'influence', loadComponent: () => import('./features/simulation-dashboard/influence/influence.component').then(c => c.InfluenceComponent) },
      { path: 'report',    loadComponent: () => import('./features/simulation-dashboard/report/report.component').then(c => c.ReportComponent) },
      { path: 'tools',     loadComponent: () => import('./features/simulation-dashboard/tools/tools.component').then(c => c.ToolsComponent) },

      // Backwards-Compat: alte URLs auf neue Struktur
      { path: 'karte',            redirectTo: 'network',   pathMatch: 'full' },
      { path: 'karte/network',    redirectTo: 'network',   pathMatch: 'full' },
      { path: 'karte/personas',   redirectTo: 'personas',  pathMatch: 'full' },
      { path: 'studie',           redirectTo: 'overview',  pathMatch: 'full' },
      { path: 'studie/overview',  redirectTo: 'overview',  pathMatch: 'full' },
      { path: 'studie/sentiment', redirectTo: 'sentiment', pathMatch: 'full' },
      { path: 'studie/influence', redirectTo: 'influence', pathMatch: 'full' },
      { path: 'gespraech',        redirectTo: 'report',    pathMatch: 'full' },
      { path: 'gespraech/report', redirectTo: 'report',    pathMatch: 'full' },
      { path: 'gespraech/chat',   redirectTo: 'tools',     pathMatch: 'full' },
    ],
  },
  { path: '**', redirectTo: '' },
];
