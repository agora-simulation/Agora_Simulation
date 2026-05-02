import { Component, signal, inject } from '@angular/core';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [FormsModule],
  styles: [`
    :host {
      display: block;
      min-height: 100vh;
      background: var(--bg);
    }

    .login-shell {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 32px 20px;
    }

    .login-card {
      width: 100%;
      max-width: 460px;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-xl);
      padding: 48px;
      box-shadow: var(--shadow-lg);
    }

    .brand-mark {
      width: 64px;
      height: 64px;
      background: linear-gradient(135deg, var(--primary) 0%, var(--primary-d) 100%);
      color: #fff;
      font-size: 32px;
      font-weight: 800;
      letter-spacing: -0.04em;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: var(--radius-lg);
      margin-bottom: 28px;
      box-shadow: 0 4px 16px rgba(42, 108, 184, 0.25);
    }

    .brand-title {
      font-size: 32px;
      font-weight: 800;
      letter-spacing: -0.03em;
      color: var(--ink);
      margin-bottom: 4px;
    }
    .brand-sub {
      font-size: 15px;
      color: var(--ink-2);
      margin-bottom: 36px;
    }

    .input-row {
      position: relative;
    }
    .input-row .toggle-btn {
      position: absolute;
      top: 50%;
      transform: translateY(-50%);
      right: 8px;
      padding: 6px 10px;
      background: transparent;
      border: none;
      cursor: pointer;
      color: var(--ink-3);
      font-size: 12px;
      font-weight: 600;
      border-radius: var(--radius-sm);
      transition: color 140ms ease, background 140ms ease;
    }
    .input-row .toggle-btn:hover { color: var(--ink); background: var(--surface-2); }

    .alert-error {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 12px 14px;
      background: var(--danger-l);
      color: var(--danger);
      border-radius: var(--radius);
      font-size: 13px;
      font-weight: 500;
      margin-bottom: 20px;
    }

    .help-text {
      font-size: 12.5px;
      color: var(--ink-3);
      margin-top: 24px;
      text-align: center;
      line-height: 1.5;
    }
  `],
  template: `
    <div class="login-shell">
      <div class="login-card animate-fade-in">

        <div class="brand-mark">A</div>

        <h1 class="brand-title">Agora</h1>
        <p class="brand-sub">Soziale Simulations-Engine</p>

        <form (ngSubmit)="login()">

          @if (error()) {
            <div class="alert-error" role="alert">
              <i class="pi pi-exclamation-triangle"></i>
              <span>{{ error() }}</span>
            </div>
          }

          <div class="field">
            <label for="api-key-input" class="label-required">API-Schlüssel</label>
            <div class="input-row">
              <input id="api-key-input"
                     [type]="showKey() ? 'text' : 'password'"
                     [ngModel]="apiKey()"
                     (ngModelChange)="apiKey.set($event)"
                     name="apiKey"
                     placeholder="sim_••••••••••••••••"
                     aria-label="API-Schlüssel eingeben"
                     autocomplete="off"
                     class="input input-lg"
                     style="padding-right: 86px; font-family: var(--font-mono); font-size: 14px;" />
              <button (click)="showKey.update(v => !v)"
                      type="button"
                      aria-label="{{ showKey() ? 'API-Schlüssel verbergen' : 'API-Schlüssel anzeigen' }}"
                      class="toggle-btn">
                {{ showKey() ? 'Verbergen' : 'Anzeigen' }}
              </button>
            </div>
          </div>

          <button type="submit"
                  [disabled]="loading() || !apiKey().trim()"
                  aria-label="Anmelden"
                  class="btn btn-primary btn-lg w-full"
                  style="margin-top: 8px;">
            @if (loading()) {
              <i class="pi pi-spin pi-spinner"></i>
              <span>Wird geprüft …</span>
            } @else {
              <span>Anmelden</span>
              <i class="pi pi-arrow-right" style="font-size: 12px;"></i>
            }
          </button>

          <p class="help-text">
            Du hast keinen Schlüssel? Wende dich an deine Administration.
          </p>

        </form>
      </div>
    </div>
  `,
})
export class LoginComponent {
  private router = inject(Router);
  private http = inject(HttpClient);

  apiKey = signal('');
  showKey = signal(false);
  loading = signal(false);
  error = signal('');

  login() {
    const key = this.apiKey().trim();
    if (!key) return;

    this.loading.set(true);
    this.error.set('');

    this.http.get(`${environment.apiUrl}/simulations/`, {
      headers: { 'X-API-Key': key },
      params: { limit: '1', offset: '0' },
    }).subscribe({
      next: () => {
        localStorage.setItem('sim_api_key', key);
        this.router.navigate(['/simulations']);
      },
      error: (err) => {
        this.loading.set(false);
        if (err.status === 401) {
          this.error.set('Ungültiger oder deaktivierter API-Schlüssel.');
        } else {
          this.error.set('Verbindung zum Server fehlgeschlagen.');
        }
      },
    });
  }
}
