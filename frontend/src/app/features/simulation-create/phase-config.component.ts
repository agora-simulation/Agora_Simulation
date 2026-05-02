import { Component, input, output, signal, inject, OnInit, effect } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ProviderService } from '../../core/services/provider.service';
import { Provider } from '../../core/models/provider.model';
import type { PhaseProviderEntry } from '../../core/models/provider.model';

interface ModelOption {
  id: string;
  label: string;
  tier: 'fast' | 'smart';
}

const MODEL_OPTIONS: Record<string, ModelOption[]> = {
  anthropic: [
    { id: 'claude-haiku-4-5-20251001', label: 'Claude Haiku 4.5',   tier: 'fast'  },
    { id: 'claude-sonnet-4-6',         label: 'Claude Sonnet 4.6',   tier: 'smart' },
    { id: 'claude-opus-4-7',           label: 'Claude Opus 4.7',     tier: 'smart' },
  ],
  openai: [
    { id: 'gpt-4o-mini',  label: 'GPT-4o-mini',  tier: 'fast'  },
    { id: 'gpt-5-mini',   label: 'GPT-5-mini',   tier: 'fast'  },
    { id: 'gpt-4o',       label: 'GPT-4o',        tier: 'smart' },
    { id: 'gpt-5',        label: 'GPT-5',         tier: 'smart' },
  ],
  ollama: [
    { id: 'qwen2.5:7b',   label: 'Qwen 2.5 7B',   tier: 'fast'  },
    { id: 'llama3.1:8b',  label: 'Llama 3.1 8B',   tier: 'smart' },
  ],
};

@Component({
  selector: 'app-phase-config',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div class="phase-config">
      <div class="phase-header">
        <div style="display: flex; align-items: center; gap: 6px;">
          <span class="phase-label">{{ label() }}</span>
          <span class="tooltip-wrap">
            <i class="pi pi-info-circle tooltip-icon"></i>
            <span class="tooltip-box">{{ phaseTooltip() }}</span>
          </span>
        </div>
        <span class="phase-hint">{{ hint() }}</span>
      </div>

      @for (entry of entries(); track $index; let i = $index) {
        <div class="entry-row">
          <!-- Provider -->
          <div class="entry-field" style="flex: 2;">
            <div class="label-with-info">
              <label>Provider</label>
              <span class="tooltip-wrap">
                <i class="pi pi-info-circle tooltip-icon"></i>
                <span class="tooltip-box">Welcher KI-Anbieter diesen Teil der Simulation bearbeitet. Du kannst mehrere Provider pro Phase nutzen und die Last per Gewichtung verteilen.</span>
              </span>
            </div>
            <select class="input input-sm" [ngModel]="entry.provider_id"
                    (ngModelChange)="onProviderChange(i, $event)">
              @for (p of providers(); track p.id) {
                <option [value]="p.id">{{ p.name }}</option>
              }
            </select>
          </div>

          <!-- Model -->
          <div class="entry-field" style="flex: 2;">
            <div class="label-with-info">
              <label>Modell</label>
              <span class="tooltip-wrap">
                <i class="pi pi-info-circle tooltip-icon"></i>
                <span class="tooltip-box">Das konkrete KI-Modell. Schnelle Modelle (Haiku, GPT-5-mini) sind guenstiger und reichen fuer einfache Aktionen. Qualitaetsmodelle (Sonnet, GPT-5) liefern bessere Ergebnisse bei komplexen Aufgaben wie Persona-Generierung oder Analysen.</span>
              </span>
            </div>
            <select class="input input-sm" [ngModel]="entry.model"
                    (ngModelChange)="updateEntry(i, 'model', $event)">
              @for (m of getModelsForEntry(i); track m.id) {
                <option [value]="m.id">{{ m.label }} ({{ m.tier }})</option>
              }
            </select>
          </div>

          <!-- Weight -->
          <div class="entry-field" style="flex: 1;">
            <div class="label-with-info">
              <label>Anteil %</label>
              <span class="tooltip-wrap">
                <i class="pi pi-info-circle tooltip-icon"></i>
                <span class="tooltip-box">Wie viel Prozent der API-Calls dieser Provider uebernimmt. Bei einem einzelnen Provider immer 100%. Bei zwei Providern z.B. 60/40 — die Calls werden zufaellig nach Gewichtung verteilt.</span>
              </span>
            </div>
            <input type="number" class="input input-sm" [ngModel]="entry.weight"
                   (ngModelChange)="updateEntry(i, 'weight', +$event)"
                   min="1" max="100" />
          </div>

          <!-- Temperature -->
          <div class="entry-field" style="flex: 1;">
            <div class="label-with-info">
              <label>Temp</label>
              <span class="tooltip-wrap">
                <i class="pi pi-info-circle tooltip-icon"></i>
                <span class="tooltip-box tooltip-box-wide">Steuert die Kreativitaet der KI (0.0 - 2.0). Niedrig (0.1-0.3): konsistent, vorhersagbar — gut fuer Analysen. Mittel (0.5-0.8): ausgewogen — Standard fuer die meisten Aufgaben. Hoch (0.9-1.5): kreativ, ueberraschend — gut fuer diverse Persona-Generierung. Ueber 1.5: experimentell, kann unbrauchbare Ergebnisse liefern.</span>
              </span>
            </div>
            <input type="number" class="input input-sm" [ngModel]="entry.temperature"
                   (ngModelChange)="updateEntry(i, 'temperature', $event === '' ? null : +$event)"
                   min="0" max="2" step="0.1" placeholder="0.7" />
          </div>

          <!-- top_p -->
          <div class="entry-field" style="flex: 1;">
            <div class="label-with-info">
              <label>Top P</label>
              <span class="tooltip-wrap">
                <i class="pi pi-info-circle tooltip-icon"></i>
                <span class="tooltip-box tooltip-box-wide">Nucleus Sampling (0.0 - 1.0). Begrenzt die Wortauswahl auf die wahrscheinlichsten Tokens, deren kumulative Wahrscheinlichkeit Top P erreicht. 0.9 = nur die Top-90% der wahrscheinlichen Woerter. 0.1 = nur die allerwahrscheinlichsten Woerter. Leer lassen = Provider-Default. Nicht gleichzeitig mit Temperature extrem einstellen.</span>
              </span>
            </div>
            <input type="number" class="input input-sm" [ngModel]="entry.top_p"
                   (ngModelChange)="updateEntry(i, 'top_p', $event === '' ? null : +$event)"
                   min="0" max="1" step="0.05" placeholder="—" />
          </div>

          <!-- top_k (nur bei Anthropic/Ollama) -->
          @if (getProviderType(entry.provider_id) !== 'openai') {
            <div class="entry-field" style="flex: 1;">
              <div class="label-with-info">
                <label>Top K</label>
                <span class="tooltip-wrap">
                  <i class="pi pi-info-circle tooltip-icon"></i>
                  <span class="tooltip-box tooltip-box-wide">Begrenzt die Wortauswahl auf die K wahrscheinlichsten Tokens. Top K = 40 bedeutet: nur die 40 wahrscheinlichsten naechsten Woerter werden betrachtet. Niedrige Werte (5-10): sehr fokussiert. Hohe Werte (100+): mehr Vielfalt. Leer lassen = Provider-Default. Nicht bei OpenAI verfuegbar.</span>
                </span>
              </div>
              <input type="number" class="input input-sm" [ngModel]="entry.top_k"
                     (ngModelChange)="updateEntry(i, 'top_k', $event === '' ? null : +$event)"
                     min="1" step="1" placeholder="—" />
            </div>
          }

          <!-- Remove -->
          @if (entries().length > 1) {
            <button type="button" class="btn-icon-sm" (click)="removeEntry(i)" aria-label="Entfernen"
                    title="Diesen Provider-Eintrag entfernen">
              <i class="pi pi-times" style="font-size: 11px;"></i>
            </button>
          }
        </div>
      }

      <button type="button" class="btn btn-sm btn-tertiary" (click)="addEntry()" style="margin-top: 8px;"
              title="Einen weiteren Provider fuer diese Phase hinzufuegen — Calls werden nach Gewichtung verteilt">
        <i class="pi pi-plus" style="font-size: 10px;"></i> Provider hinzufuegen
      </button>
    </div>
  `,
  styles: [`
    .phase-config { margin-bottom: 20px; }
    .phase-header { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px; }
    .phase-label { font-size: 13.5px; font-weight: 600; color: var(--ink); }
    .phase-hint { font-size: 11.5px; color: var(--ink-4); }
    .entry-row {
      display: flex; gap: 8px; align-items: flex-end; margin-bottom: 6px;
      padding: 10px 12px; background: var(--surface); border: 1px solid var(--border);
      border-radius: var(--radius-sm);
    }
    .entry-field { display: flex; flex-direction: column; }
    .entry-field label { font-size: 10.5px; color: var(--ink-4); margin-bottom: 3px; font-weight: 500; }
    .label-with-info { display: flex; align-items: center; gap: 4px; margin-bottom: 3px; }
    .label-with-info label { margin-bottom: 0; }
    .input-sm { padding: 5px 8px; font-size: 12.5px; }
    .btn-icon-sm {
      width: 28px; height: 28px; border-radius: var(--radius-sm);
      border: 1px solid var(--border); background: var(--surface); cursor: pointer;
      display: flex; align-items: center; justify-content: center; color: var(--ink-3);
      flex-shrink: 0;
    }
    .btn-icon-sm:hover { border-color: var(--danger); color: var(--danger); }

    /* Tooltip */
    .tooltip-wrap {
      position: relative;
      display: inline-flex;
      align-items: center;
    }
    .tooltip-icon {
      font-size: 11px;
      color: var(--ink-4);
      cursor: help;
      transition: color 150ms;
    }
    .tooltip-wrap:hover .tooltip-icon { color: var(--primary); }
    .tooltip-box {
      display: none;
      position: absolute;
      bottom: calc(100% + 8px);
      left: 50%;
      transform: translateX(-50%);
      background: var(--ink);
      color: #fff;
      font-size: 11.5px;
      line-height: 1.5;
      padding: 8px 12px;
      border-radius: 6px;
      width: 220px;
      z-index: 100;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      pointer-events: none;
      font-weight: 400;
    }
    .tooltip-box-wide { width: 280px; }
    .tooltip-wrap:hover .tooltip-box { display: block; }
    .tooltip-box::after {
      content: '';
      position: absolute;
      top: 100%;
      left: 50%;
      transform: translateX(-50%);
      border: 5px solid transparent;
      border-top-color: var(--ink);
    }
  `],
})
export class PhaseConfigComponent implements OnInit {
  label = input.required<string>();
  hint = input('');
  initialEntries = input<PhaseProviderEntry[]>([]);

  entriesChange = output<PhaseProviderEntry[]>();

  private providerService = inject(ProviderService);
  providers = signal<Provider[]>([]);
  entries = signal<PhaseProviderEntry[]>([]);

  private readonly phaseTooltips: Record<string, string> = {
    'Persona-Generierung': 'Erstellt die virtuellen Personas mit Persoenlichkeit, Werten und Meinungen. Nutzt ein Qualitaetsmodell (Smart-Tier), da die Persona-Qualitaet das Simulationsergebnis stark beeinflusst.',
    'Agenten-Aktionen (Tick)': 'Jede Persona entscheidet pro Simulationstag, ob sie postet, kommentiert oder reagiert. Nutzt ein schnelles Modell (Fast-Tier), da viele Calls parallel laufen.',
    'State-Updates (Tick)': 'Aktualisiert Meinung und Stimmung jeder Persona nach ihren taeglichen Aktionen. Nutzt ein schnelles Modell (Fast-Tier). Laeuft parallel zu den Aktionen.',
    'Analyse & Report': 'Erstellt den finalen Analyse-Report mit Sentiment-Verlauf, Wendepunkten und Empfehlungen. Nutzt ein Qualitaetsmodell (Smart-Tier) fuer tiefgehende Analyse.',
  };

  phaseTooltip() {
    return this.phaseTooltips[this.label()] || '';
  }

  constructor() {
    effect(() => {
      const init = this.initialEntries();
      if (init.length > 0) {
        this.entries.set([...init]);
      }
    });
  }

  ngOnInit() {
    this.providerService.list().subscribe(providers => {
      this.providers.set(providers);
      if (this.entries().length === 0 && providers.length > 0) {
        const defaultProvider = providers.find(p => p.is_default) || providers[0];
        const type = defaultProvider.provider_type;
        const defaultModel = MODEL_OPTIONS[type]?.find(m => m.tier === 'fast')?.id || 'gpt-5-mini';
        this.entries.set([{
          provider_id: defaultProvider.id,
          model: defaultModel,
          weight: 100,
          temperature: 0.7,
          top_p: null,
          top_k: null,
        }]);
        this.emitChange();
      }
    });
  }

  getProviderType(providerId: string): string {
    return this.providers().find(p => p.id === providerId)?.provider_type || 'openai';
  }

  getModelsForEntry(index: number): ModelOption[] {
    const entry = this.entries()[index];
    if (!entry) return [];
    const type = this.getProviderType(entry.provider_id);
    return MODEL_OPTIONS[type] || [];
  }

  onProviderChange(index: number, newProviderId: string) {
    const type = this.getProviderType(newProviderId);
    const defaultModel = MODEL_OPTIONS[type]?.[0]?.id || '';
    const updated = [...this.entries()];
    updated[index] = { ...updated[index], provider_id: newProviderId, model: defaultModel };
    this.entries.set(updated);
    this.emitChange();
  }

  updateEntry(index: number, field: string, value: unknown) {
    const updated = [...this.entries()];
    updated[index] = { ...updated[index], [field]: value };
    this.entries.set(updated);
    this.emitChange();
  }

  addEntry() {
    const providers = this.providers();
    const defaultProvider = providers.find(p => p.is_default) || providers[0];
    if (!defaultProvider) return;
    const type = defaultProvider.provider_type;
    const defaultModel = MODEL_OPTIONS[type]?.find(m => m.tier === 'fast')?.id || 'gpt-5-mini';

    this.entries.update(e => [...e, {
      provider_id: defaultProvider.id,
      model: defaultModel,
      weight: 50,
      temperature: 0.7,
      top_p: null,
      top_k: null,
    }]);
    this.emitChange();
  }

  removeEntry(index: number) {
    this.entries.update(e => e.filter((_, i) => i !== index));
    this.emitChange();
  }

  private emitChange() {
    this.entriesChange.emit(this.entries());
  }
}
