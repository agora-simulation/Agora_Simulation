import { Injectable, signal } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  private darkMode = signal(this.loadTheme());
  readonly isDarkMode = this.darkMode.asReadonly();

  constructor() {
    this.applyTheme();

    // Listen for OS preference changes (only if no manual override)
    window.matchMedia('(prefers-color-scheme: dark)')
      .addEventListener('change', (e) => {
        if (!localStorage.getItem('theme')) {
          this.darkMode.set(e.matches);
          this.applyTheme();
        }
      });
  }

  toggle(): void {
    this.darkMode.update(v => !v);
    localStorage.setItem('theme', this.darkMode() ? 'dark' : 'light');
    this.applyTheme();
  }

  private applyTheme(): void {
    const el = document.documentElement;
    el.classList.toggle('dark', this.darkMode());
    el.classList.toggle('light', !this.darkMode());
  }

  private loadTheme(): boolean {
    const stored = localStorage.getItem('theme');
    if (stored) return stored === 'dark';
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  }
}
