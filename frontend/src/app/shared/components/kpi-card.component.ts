import { Component, input } from '@angular/core';

@Component({
  selector: 'app-kpi-card',
  standalone: true,
  template: `
    <div class="card card-hover kpi-stat" [attr.aria-label]="label() + ': ' + value()">
      <p class="kpi-label">{{ label() }}</p>
      <p class="kpi-value">{{ value() }}</p>
      @if (subtitle()) {
        <p class="kpi-sub">{{ subtitle() }}</p>
      }
    </div>
  `,
  styles: [`
    .kpi-stat {
      padding: 20px;
    }
    .kpi-label {
      font-size: 14px;
      font-weight: 500;
      color: var(--ink-3);
      margin-bottom: 8px;
    }
    .kpi-value {
      font-family: var(--font-sans);
      font-size: 32px;
      line-height: 1.05;
      font-weight: 700;
      color: var(--ink);
      letter-spacing: -0.02em;
      font-variant-numeric: tabular-nums;
    }
    .kpi-sub {
      margin-top: 6px;
      font-size: 12px;
      color: var(--ink-4);
    }
  `],
})
export class KpiCardComponent {
  label = input.required<string>();
  value = input.required<string | number>();
  subtitle = input<string>();
}
