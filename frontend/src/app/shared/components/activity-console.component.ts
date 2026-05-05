import {
  Component,
  Input,
  OnChanges,
  OnDestroy,
  SimpleChanges,
  inject,
  signal,
  ViewChild,
  ElementRef,
  AfterViewChecked,
} from '@angular/core';
import { Subscription } from 'rxjs';
import { SseService } from '../../core/services/sse.service';
import { SimulationStatus } from '../../core/models/simulation.model';

interface LogLine {
  timestamp: string;
  level: 'INFO' | 'TICK' | 'OK' | 'ERROR' | 'IDLE';
  text: string;
}

@Component({
  selector: 'app-activity-console',
  standalone: true,
  template: `
    @if (shouldRender()) {
      <aside
        class="activity-console"
        [class.activity-console-collapsed]="!expanded()"
        [class.activity-console-empty]="isEmptyHint()"
        role="region"
        aria-label="Aktivitäts-Konsole"
      >
        <!-- Header (light) -->
        <header class="ac-header" (click)="toggle()">
          <div class="ac-header-left">
            @if (simulationStatus === 'running') {
              <span class="dot dot-pulse" aria-hidden="true"></span>
              <span class="ac-title">Aktivität</span>
              <span class="ac-status-label ac-status-running">LIVE</span>
            } @else if (simulationStatus === 'completed') {
              <span class="dot" style="background: var(--success);" aria-hidden="true"></span>
              <span class="ac-title">Aktivität</span>
              <span class="ac-status-label ac-status-ok">Abgeschlossen</span>
            } @else if (simulationStatus === 'failed') {
              <span class="dot" style="background: var(--danger);" aria-hidden="true"></span>
              <span class="ac-title">Aktivität</span>
              <span class="ac-status-label ac-status-err">Fehler</span>
            } @else {
              <span class="dot" style="background: var(--ink-4);" aria-hidden="true"></span>
              <span class="ac-title">Aktivität</span>
              <span class="ac-status-label ac-status-idle">Inaktiv</span>
            }
          </div>

          <div class="ac-header-right">
            @if (currentTick() !== null) {
              <span class="ac-counter">
                Tick {{ pad(currentTick()!) }}/{{ pad(totalTicks()) }}
              </span>
            }
            <span class="ac-counter ac-line-count">{{ logs().length }} Zeilen</span>
            <button
              type="button"
              class="ac-toggle"
              [attr.aria-label]="expanded() ? 'Konsole einklappen' : 'Konsole ausklappen'"
              [attr.aria-expanded]="expanded()"
              (click)="$event.stopPropagation(); toggle()"
            >
              <i class="pi" [class.pi-chevron-down]="expanded()" [class.pi-chevron-up]="!expanded()"></i>
            </button>
          </div>
        </header>

        <!-- Body (dark code surface) -->
        @if (expanded()) {
          <div class="ac-body" #body role="log" aria-live="polite">
            @if (!simulationId) {
              <div class="ac-empty">
                <span class="ac-line ac-line-idle">[--:--:--] IDLE: Keine aktive Simulation.</span>
              </div>
            } @else if (logs().length === 0) {
              <div class="ac-empty">
                <span class="ac-line ac-line-idle">
                  [{{ nowStamp() }}] INFO: Warte auf Ereignisse …
                </span>
              </div>
            } @else {
              @for (line of logs(); track $index) {
                <div
                  class="ac-line"
                  [class.ac-line-tick]="line.level === 'TICK'"
                  [class.ac-line-ok]="line.level === 'OK'"
                  [class.ac-line-err]="line.level === 'ERROR'"
                  [class.ac-line-idle]="line.level === 'IDLE'"
                >
                  [{{ line.timestamp }}] {{ line.level }}: {{ line.text }}
                </div>
              }
            }
          </div>
        }
      </aside>
    }
  `,
  styles: [`
    :host {
      display: block;
      position: sticky;
      bottom: 0;
      left: 0;
      right: 0;
      z-index: 30;
    }
    .activity-console {
      background: var(--surface);
      border-top: 2px solid var(--ink);
      box-shadow: 0 -4px 14px rgba(0, 0, 0, 0.06);
      display: flex;
      flex-direction: column;
      max-height: 220px;
      transition: max-height 220ms ease;
    }
    .activity-console-collapsed { max-height: 44px; }
    .activity-console-empty { max-height: 36px; opacity: 0.85; }
    .activity-console-empty .ac-toggle { display: none; }

    .ac-header {
      height: 44px;
      flex: 0 0 44px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0 24px;
      cursor: pointer;
      user-select: none;
      background: var(--surface);
    }
    .activity-console-empty .ac-header { height: 36px; flex: 0 0 36px; cursor: default; }

    .ac-header-left  { display: flex; align-items: center; gap: 10px; }
    .ac-header-right { display: flex; align-items: center; gap: 14px; }

    .ac-title {
      font-family: var(--font-sans);
      font-size: 14px;
      font-weight: 600;
      color: var(--ink);
      letter-spacing: -0.005em;
    }
    .ac-status-label {
      font-family: var(--font-sans);
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      padding: 2px 8px;
      border-radius: 999px;
    }
    .ac-status-running { background: var(--primary-l); color: var(--primary); }
    .ac-status-ok      { background: var(--success-l); color: var(--success); }
    .ac-status-err     { background: var(--danger-l);  color: var(--danger); }
    .ac-status-idle    { background: var(--surface-3); color: var(--ink-3); }

    .ac-counter {
      font-family: var(--font-mono);
      font-size: 12px;
      color: var(--ink-3);
      letter-spacing: 0.02em;
    }
    .ac-line-count { color: var(--ink-4); }

    .ac-toggle {
      background: transparent;
      color: var(--ink-3);
      border: 1px solid var(--border-strong);
      border-radius: var(--radius-sm);
      width: 26px;
      height: 26px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      padding: 0;
      transition: color 140ms ease, border-color 140ms ease, background 140ms ease;
    }
    .ac-toggle:hover { color: var(--ink); border-color: var(--ink-3); background: var(--surface-2); }
    .ac-toggle .pi { font-size: 12px; }

    .ac-body {
      flex: 1 1 auto;
      overflow-y: auto;
      padding: 10px 24px 14px;
      background: #0f1419;
      color: #d4dae2;
      font-family: var(--font-mono);
    }
    .ac-body::-webkit-scrollbar { width: 8px; }
    .ac-body::-webkit-scrollbar-track { background: #0a0e12; }
    .ac-body::-webkit-scrollbar-thumb { background: #2a3038; border-radius: 4px; }

    .ac-line {
      font-size: 13px;
      line-height: 1.6;
      color: #d4dae2;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .ac-line-tick { color: #9bb1c7; }
    .ac-line-ok   { color: #6fc28a; }
    .ac-line-err  { color: var(--primary); }
    .ac-line-idle { color: #6e7682; }
    .ac-empty { padding-top: 4px; }
  `],
})
export class ActivityConsoleComponent implements OnChanges, OnDestroy, AfterViewChecked {
  @Input() simulationId: string | null = null;
  @Input() simulationStatus: SimulationStatus = 'pending';

  @ViewChild('body') private bodyRef?: ElementRef<HTMLDivElement>;

  private sseService = inject(SseService);
  private sseSub?: Subscription;
  private lastTick = -1;
  private finalLogged = false;
  private shouldAutoScroll = false;

  expanded = signal<boolean>(true);
  logs = signal<LogLine[]>([]);
  currentTick = signal<number | null>(null);
  totalTicks = signal<number>(0);

  /** Komplett ausgeblendet, wenn keine Sim-ID vorhanden. */
  shouldRender(): boolean {
    if (!this.simulationId) return false;
    // Wenn nicht running und keine Logs → ganz ausblenden
    if (this.simulationStatus !== 'running' && this.logs().length === 0) return false;
    return true;
  }
  /** Schmaler "Inaktiv"-Streifen statt voller Konsole. */
  isEmptyHint(): boolean {
    return this.simulationStatus !== 'running' && this.logs().length === 0;
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['simulationId']) {
      this.resetState();
      this.tryConnect();
    }
    if (changes['simulationStatus'] && !changes['simulationId']) {
      // Resume: status changed from failed/completed → running → reset for new stream
      const prev = changes['simulationStatus'].previousValue;
      const curr = changes['simulationStatus'].currentValue;
      if ((prev === 'failed' || prev === 'completed') && curr === 'running') {
        this.sseSub?.unsubscribe();
        this.sseSub = undefined;
        this.finalLogged = false;
        this.lastTick = -1;
        this.appendLog('INFO', 'Simulation wird fortgesetzt...');
      }
      this.tryConnect();
      this.maybeLogFinalStatus();
    }
  }

  ngOnDestroy(): void {
    this.sseSub?.unsubscribe();
  }

  ngAfterViewChecked(): void {
    if (this.shouldAutoScroll && this.bodyRef) {
      const el = this.bodyRef.nativeElement;
      el.scrollTop = el.scrollHeight;
      this.shouldAutoScroll = false;
    }
  }

  toggle(): void {
    this.expanded.update(v => !v);
  }

  pad(n: number): string {
    return n.toString().padStart(2, '0');
  }

  nowStamp(): string {
    return this.formatTime(new Date());
  }

  private resetState(): void {
    this.sseSub?.unsubscribe();
    this.sseSub = undefined;
    this.logs.set([]);
    this.currentTick.set(null);
    this.totalTicks.set(0);
    this.lastTick = -1;
    this.finalLogged = false;
  }

  private tryConnect(): void {
    if (!this.simulationId) return;
    if (this.simulationStatus !== 'running') {
      this.maybeLogFinalStatus();
      return;
    }
    if (this.sseSub) return;

    this.appendLog('INFO', `Verbinde mit Stream · sim ${this.simulationId.substring(0, 8)} …`);

    this.sseSub = this.sseService.connect(this.simulationId).subscribe({
      next: (event) => {
        this.totalTicks.set(event.total_ticks ?? 0);

        if (
          typeof event.current_tick === 'number' &&
          event.current_tick !== this.lastTick
        ) {
          this.lastTick = event.current_tick;
          this.currentTick.set(event.current_tick);
          this.appendLog(
            'TICK',
            `${this.pad(event.current_tick)}/${this.pad(event.total_ticks ?? 0)} · status: ${event.status}`
          );
        }

        if (event.status === 'completed' && !this.finalLogged) {
          this.finalLogged = true;
          this.appendLog('OK', 'SIMULATION COMPLETED');
        } else if (event.status === 'failed' && !this.finalLogged) {
          this.finalLogged = true;
          this.appendLog('ERROR', 'SIMULATION FAILED');
        }
      },
      error: () => {
        this.appendLog('ERROR', 'Stream-Verbindung unterbrochen.');
      },
    });
  }

  private maybeLogFinalStatus(): void {
    if (!this.simulationId || this.finalLogged) return;
    if (this.simulationStatus === 'completed') {
      this.finalLogged = true;
      this.appendLog('OK', 'SIMULATION COMPLETED');
    } else if (this.simulationStatus === 'failed') {
      this.finalLogged = true;
      this.appendLog('ERROR', 'SIMULATION FAILED');
    }
  }

  private appendLog(level: LogLine['level'], text: string): void {
    const line: LogLine = { timestamp: this.formatTime(new Date()), level, text };
    this.logs.update(arr => {
      const next = [...arr, line];
      // Cap to prevent unbounded growth
      if (next.length > 500) next.splice(0, next.length - 500);
      return next;
    });
    this.shouldAutoScroll = true;
  }

  private formatTime(d: Date): string {
    const hh = d.getHours().toString().padStart(2, '0');
    const mm = d.getMinutes().toString().padStart(2, '0');
    const ss = d.getSeconds().toString().padStart(2, '0');
    return `${hh}:${mm}:${ss}`;
  }
}
