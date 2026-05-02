import { Component, input, output, signal, inject, OnInit, effect, computed } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ProviderService } from '../../core/services/provider.service';
import { Provider } from '../../core/models/provider.model';
import type { PhaseProviderEntry, ProviderCapabilities, ModelCapabilities, ParamCapability } from '../../core/models/provider.model';

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
              @if (getProviderNotes(entry.provider_id).length > 0) {
                <span class="tooltip-wrap" [attr.aria-label]="'Hinweise zu ' + getProviderType(entry.provider_id)">
                  <i class="pi pi-info-circle tooltip-icon"></i>
                  <span class="tooltip-box tooltip-box-wide">
                    @for (note of getProviderNotes(entry.provider_id); track note) {
                      <span style="display: block; margin-bottom: 4px;">{{ note }}</span>
                    }
                  </span>
                </span>
              }
            </div>
            <select class="input input-sm" [ngModel]="entry.provider_id"
                    (ngModelChange)="onProviderChange(i, $event)"
                    [attr.aria-label]="'Provider fuer ' + label()">
              @for (p of providers(); track p.id) {
                <option [value]="p.id">{{ p.name }}</option>
              }
            </select>
          </div>

          <!-- Model -->
          <div class="entry-field" style="flex: 2;">
            <div class="label-with-info">
              <label>Modell</label>
            </div>
            <select class="input input-sm" [ngModel]="entry.model"
                    (ngModelChange)="updateEntry(i, 'model', $event)">
              @for (m of getModelsForEntry(i); track m.model_id) {
                <option [value]="m.model_id">{{ m.label }} ({{ m.tier }})</option>
              }
            </select>
          </div>

          <!-- Weight -->
          <div class="entry-field" style="flex: 1;">
            <div class="label-with-info">
              <label>Anteil %</label>
            </div>
            <input type="number" class="input input-sm" [ngModel]="entry.weight"
                   (ngModelChange)="updateEntry(i, 'weight', +$event)"
                   min="1" max="100" />
          </div>

          <!-- Temperature -->
          <div class="entry-field" style="flex: 1;"
               [class.field-disabled]="!isParamSupported(i, 'temperature')">
            <div class="label-with-info">
              <label>Temp</label>
              @if (!isParamSupported(i, 'temperature')) {
                <span class="tooltip-wrap">
                  <i class="pi pi-lock tooltip-icon lock-icon"></i>
                  <span class="tooltip-box tooltip-box-wide">{{ getParamReason(i, 'temperature') }}</span>
                </span>
              }
            </div>
            @if (!isParamSupported(i, 'temperature')) {
              <input type="text" class="input input-sm input-locked" value="—" disabled
                     [title]="getParamReason(i, 'temperature')" />
            } @else {
              <input type="number" class="input input-sm" [ngModel]="entry.temperature"
                     (ngModelChange)="updateEntry(i, 'temperature', $event === '' ? null : +$event)"
                     min="0" max="2" step="0.1" [placeholder]="getParamDefault(i, 'temperature') ?? 0.7" />
            }
          </div>

          <!-- top_p -->
          <div class="entry-field" style="flex: 1;"
               [class.field-disabled]="!isParamSupported(i, 'top_p')">
            <div class="label-with-info">
              <label>Top P</label>
              @if (!isParamSupported(i, 'top_p')) {
                <span class="tooltip-wrap">
                  <i class="pi pi-lock tooltip-icon lock-icon"></i>
                  <span class="tooltip-box tooltip-box-wide">{{ getParamReason(i, 'top_p') }}</span>
                </span>
              }
            </div>
            @if (!isParamSupported(i, 'top_p')) {
              <input type="text" class="input input-sm input-locked" value="—" disabled
                     [title]="getParamReason(i, 'top_p')" />
            } @else {
              <input type="number" class="input input-sm" [ngModel]="entry.top_p"
                     (ngModelChange)="updateEntry(i, 'top_p', $event === '' ? null : +$event)"
                     min="0" max="1" step="0.05" placeholder="—" />
            }
          </div>

          <!-- top_k -->
          <div class="entry-field" style="flex: 1;"
               [class.field-disabled]="!isParamSupported(i, 'top_k')">
            <div class="label-with-info">
              <label>Top K</label>
              @if (!isParamSupported(i, 'top_k')) {
                <span class="tooltip-wrap">
                  <i class="pi pi-lock tooltip-icon lock-icon"></i>
                  <span class="tooltip-box tooltip-box-wide">{{ getParamReason(i, 'top_k') }}</span>
                </span>
              }
            </div>
            @if (!isParamSupported(i, 'top_k')) {
              <input type="text" class="input input-sm input-locked" value="—" disabled
                     [title]="getParamReason(i, 'top_k')" />
            } @else {
              <input type="number" class="input input-sm" [ngModel]="entry.top_k"
                     (ngModelChange)="updateEntry(i, 'top_k', $event === '' ? null : +$event)"
                     min="1" step="1" placeholder="—" />
            }
          </div>

          <!-- Remove -->
          @if (entries().length > 1) {
            <button type="button" class="btn-icon-sm" (click)="removeEntry(i)" aria-label="Entfernen"
                    title="Diesen Provider-Eintrag entfernen">
              <i class="pi pi-times" style="font-size: 11px;"></i>
            </button>
          }
        </div>

        <!-- Provider Notes sind jetzt als Tooltip im Provider-Label integriert -->
      }

      <button type="button" class="btn btn-sm btn-tertiary" (click)="addEntry()" style="margin-top: 8px;"
              title="Einen weiteren Provider fuer diese Phase hinzufuegen">
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

    /* Disabled/Locked Fields */
    .field-disabled { opacity: 0.5; }
    .input-locked {
      background: var(--surface-2, #f5f5f5) !important;
      color: var(--ink-4) !important;
      cursor: not-allowed;
      text-align: center;
    }
    .lock-icon { color: var(--ink-4); font-size: 10px; }

    /* Provider Notes sind jetzt Tooltips */

    /* Tooltip */
    .tooltip-wrap { position: relative; display: inline-flex; align-items: center; }
    .tooltip-icon { font-size: 11px; color: var(--ink-4); cursor: help; transition: color 150ms; }
    .tooltip-wrap:hover .tooltip-icon { color: var(--primary); }
    .tooltip-box {
      display: none; position: absolute; bottom: calc(100% + 8px); left: 50%;
      transform: translateX(-50%); background: var(--ink); color: #fff;
      font-size: 11.5px; line-height: 1.5; padding: 8px 12px; border-radius: 6px;
      width: 220px; z-index: 100; box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      pointer-events: none; font-weight: 400;
    }
    .tooltip-box-wide { width: 280px; }
    .tooltip-wrap:hover .tooltip-box { display: block; }
    .tooltip-box::after {
      content: ''; position: absolute; top: 100%; left: 50%;
      transform: translateX(-50%); border: 5px solid transparent; border-top-color: var(--ink);
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
  capabilities = signal<ProviderCapabilities[]>([]);

  private readonly phaseTooltips: Record<string, string> = {
    'Persona-Generierung': 'Erstellt die virtuellen Personas. Nutzt ein Qualitaetsmodell (Smart-Tier), da die Persona-Qualitaet das Simulationsergebnis stark beeinflusst.',
    'Agenten-Aktionen (Tick)': 'Jede Persona entscheidet pro Simulationstag, ob sie postet, kommentiert oder reagiert. Nutzt ein schnelles Modell (Fast-Tier).',
    'State-Updates (Tick)': 'Aktualisiert Meinung und Stimmung jeder Persona. Nutzt ein schnelles Modell (Fast-Tier).',
    'Analyse & Report': 'Erstellt den finalen Analyse-Report. Nutzt ein Qualitaetsmodell (Smart-Tier) fuer tiefgehende Analyse.',
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
    // Capabilities und Provider parallel laden
    this.providerService.getCapabilities().subscribe(caps => {
      this.capabilities.set(caps);
    });

    this.providerService.list().subscribe(providers => {
      this.providers.set(providers);
      if (this.entries().length === 0 && providers.length > 0) {
        const defaultProvider = providers.find(p => p.is_default) || providers[0];
        const models = this.getModelsForProvider(defaultProvider.provider_type);
        const defaultModel = models.find(m => m.tier === 'fast')?.model_id || models[0]?.model_id || '';
        this.entries.set([{
          provider_id: defaultProvider.id,
          model: defaultModel,
          weight: 100,
          temperature: null,  // null = Provider-Default
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

  getModelsForProvider(providerType: string): ModelCapabilities[] {
    const caps = this.capabilities().find(c => c.provider_type === providerType);
    return caps?.models || [];
  }

  getModelsForEntry(index: number): ModelCapabilities[] {
    const entry = this.entries()[index];
    if (!entry) return [];
    const type = this.getProviderType(entry.provider_id);
    return this.getModelsForProvider(type);
  }

  getModelCaps(providerId: string, modelId: string): ModelCapabilities | null {
    const type = this.getProviderType(providerId);
    const caps = this.capabilities().find(c => c.provider_type === type);
    return caps?.models.find(m => m.model_id === modelId) || null;
  }

  getProviderNotes(providerId: string): string[] {
    const type = this.getProviderType(providerId);
    const caps = this.capabilities().find(c => c.provider_type === type);
    return caps?.notes || [];
  }

  /** Prüft ob ein Sampling-Parameter für den Entry an Index i unterstützt wird. */
  isParamSupported(index: number, param: 'temperature' | 'top_p' | 'top_k'): boolean {
    const entry = this.entries()[index];
    if (!entry) return true;
    const caps = this.getModelCaps(entry.provider_id, entry.model);
    if (!caps) return true; // Kein Caps geladen → alles erlauben
    return caps[param].supported;
  }

  /** Gibt den Grund zurück, warum ein Parameter nicht unterstützt wird. */
  getParamReason(index: number, param: 'temperature' | 'top_p' | 'top_k'): string {
    const entry = this.entries()[index];
    if (!entry) return '';
    const caps = this.getModelCaps(entry.provider_id, entry.model);
    return caps?.[param]?.reason || 'Nicht verfuegbar fuer dieses Modell.';
  }

  /** Gibt den Default-Wert für einen Parameter zurück. */
  getParamDefault(index: number, param: 'temperature' | 'top_p' | 'top_k'): number | null {
    const entry = this.entries()[index];
    if (!entry) return null;
    const caps = this.getModelCaps(entry.provider_id, entry.model);
    return caps?.[param]?.default ?? null;
  }

  onProviderChange(index: number, newProviderId: string) {
    const type = this.getProviderType(newProviderId);
    const models = this.getModelsForProvider(type);
    const defaultModel = models[0]?.model_id || '';
    const updated = [...this.entries()];
    // Reset sampling params when switching provider (sie koennten nicht mehr supported sein)
    updated[index] = {
      ...updated[index],
      provider_id: newProviderId,
      model: defaultModel,
      temperature: null,
      top_p: null,
      top_k: null,
    };
    this.entries.set(updated);
    this.emitChange();
  }

  updateEntry(index: number, field: string, value: unknown) {
    const updated = [...this.entries()];
    updated[index] = { ...updated[index], [field]: value };

    // Wenn Model gewechselt: unsupported params auf null setzen
    if (field === 'model') {
      const caps = this.getModelCaps(updated[index].provider_id, value as string);
      if (caps) {
        if (!caps.temperature.supported) updated[index].temperature = null;
        if (!caps.top_p.supported) updated[index].top_p = null;
        if (!caps.top_k.supported) updated[index].top_k = null;
      }
    }

    this.entries.set(updated);
    this.emitChange();
  }

  addEntry() {
    const providers = this.providers();
    const defaultProvider = providers.find(p => p.is_default) || providers[0];
    if (!defaultProvider) return;
    const models = this.getModelsForProvider(defaultProvider.provider_type);
    const defaultModel = models.find(m => m.tier === 'fast')?.model_id || models[0]?.model_id || '';

    this.entries.update(e => [...e, {
      provider_id: defaultProvider.id,
      model: defaultModel,
      weight: 50,
      temperature: null,
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
