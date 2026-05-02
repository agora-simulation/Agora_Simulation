import { Component, inject, signal } from '@angular/core';
import { Router, RouterOutlet, RouterLink, RouterLinkActive, NavigationEnd } from '@angular/router';
import { ThemeService } from './core/services/theme.service';
import { filter } from 'rxjs';
import { toSignal } from '@angular/core/rxjs-interop';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  protected theme = inject(ThemeService);
  private router = inject(Router);

  protected showApiKeyDialog = signal(false);
  protected showLogoutConfirm = signal(false);
  protected apiKeyInput = signal('');

  // Track if we're on the login page
  protected isLoginPage = signal(false);

  constructor() {
    this.router.events.pipe(
      filter((e): e is NavigationEnd => e instanceof NavigationEnd)
    ).subscribe(e => {
      const url = e.urlAfterRedirects;
      this.isLoginPage.set(url === '/' || url.startsWith('/login'));
    });
  }

  protected hasApiKey(): boolean {
    return !!localStorage.getItem('sim_api_key');
  }

  protected confirmLogout() {
    this.showLogoutConfirm.set(true);
  }

  protected logout() {
    this.showLogoutConfirm.set(false);
    localStorage.removeItem('sim_api_key');
    this.router.navigate(['/login']);
  }

  protected openApiKeyDialog() {
    this.apiKeyInput.set(localStorage.getItem('sim_api_key') || '');
    this.showApiKeyDialog.set(true);
  }

  protected saveApiKey() {
    const key = this.apiKeyInput().trim();
    if (key) {
      localStorage.setItem('sim_api_key', key);
    } else {
      localStorage.removeItem('sim_api_key');
    }
    this.showApiKeyDialog.set(false);
  }
}
