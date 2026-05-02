import { Component, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { SimulationService } from '../../core/services/simulation.service';
import { ProviderService } from '../../core/services/provider.service';
import { SimulationCreate, LlmProvider } from '../../core/models/simulation.model';
import { SimulationProviderConfig, PhaseProviderEntry, Preset, CostEstimate, Provider } from '../../core/models/provider.model';
import { PhaseConfigComponent } from './phase-config.component';

@Component({
  selector: 'app-simulation-create',
  standalone: true,
  imports: [FormsModule, RouterLink, PhaseConfigComponent],
  templateUrl: './simulation-create.component.html',
})
export class SimulationCreateComponent {
  private simService = inject(SimulationService);
  private providerService = inject(ProviderService);
  private router = inject(Router);

  currentStep = signal(1);
  submitting = signal(false);

  // Step 1: Product
  name = signal('');
  productDescription = signal('');
  targetMarket = signal('');
  industry = signal('');

  // Step 2: Configuration
  personaCount = signal(30);
  tickCount = signal(15);
  llmProvider = signal<LlmProvider>('anthropic');

  readonly providers: { id: LlmProvider; label: string; sub: string; icon: string }[] = [
    { id: 'anthropic', label: 'Claude (Anthropic)', sub: 'Sonnet 4.6 + Haiku 4.5', icon: 'pi-sparkles' },
    { id: 'openai',    label: 'OpenAI',             sub: 'GPT-5 + GPT-5-mini',     icon: 'pi-bolt' },
  ];

  // Modell-Wahl pro Rolle (Standard / Premium / Custom)
  readonly modelModes = [
    { id: 'standard', label: 'Standard', desc: 'Schnellmodell für Aktionen, Qualitätsmodell für Persona-Gen + Report' },
    { id: 'premium',  label: 'Premium',  desc: 'Qualitätsmodell für ALLES — teurer aber kohärenter' },
    { id: 'custom',   label: 'Custom',   desc: 'Modelle pro Rolle frei wählen' },
  ] as const;
  modelMode = signal<'standard' | 'premium' | 'custom'>('standard');
  customModelFast = signal<string>('');
  customModelSmart = signal<string>('');
  showAdvanced = signal(false);

  // Modell-Optionen pro Provider — Anzeigeliste für Custom-Dropdowns
  readonly modelOptions: Record<LlmProvider, { id: string; label: string; tier: 'fast' | 'smart' }[]> = {
    anthropic: [
      { id: 'claude-haiku-4-5-20251001', label: 'Claude Haiku 4.5 (schnell, günstig)',     tier: 'fast'  },
      { id: 'claude-sonnet-4-6',         label: 'Claude Sonnet 4.6 (Standard-Qualität)',   tier: 'smart' },
      { id: 'claude-opus-4-7',           label: 'Claude Opus 4.7 (Top-Qualität, teuer)',   tier: 'smart' },
    ],
    openai: [
      { id: 'gpt-4o-mini',  label: 'GPT-4o-mini (Legacy, sehr günstig)', tier: 'fast'  },
      { id: 'gpt-5-mini',   label: 'GPT-5-mini (schnell, hohe TPM)',     tier: 'fast'  },
      { id: 'gpt-4o',       label: 'GPT-4o (Legacy, ausgewogen)',        tier: 'smart' },
      { id: 'gpt-5',        label: 'GPT-5 (Top-Qualität)',               tier: 'smart' },
    ],
    ollama: [
      { id: 'qwen2.5:7b',   label: 'Qwen 2.5 7B (Lokal)',   tier: 'fast'  },
      { id: 'llama3.1:8b',  label: 'Llama 3.1 8B (Lokal)',   tier: 'smart' },
    ],
  };

  /** Aktuelle Modell-Optionen für Fast-Tier abhängig vom Provider. */
  fastModelOptions() {
    return this.modelOptions[this.llmProvider()].filter(m => m.tier === 'fast');
  }
  smartModelOptions() {
    return this.modelOptions[this.llmProvider()].filter(m => m.tier === 'smart');
  }

  // Presets
  readonly presets = [
    { label: 'Schnelltest', icon: 'pi-bolt', personas: 10, ticks: 5, desc: '~2 Min, günstig' },
    { label: 'Standard', icon: 'pi-chart-bar', personas: 30, ticks: 15, desc: '~8 Min, empfohlen' },
    { label: 'Deep Dive', icon: 'pi-search', personas: 50, ticks: 20, desc: '~20 Min, detailliert' },
    { label: 'Enterprise', icon: 'pi-building', personas: 100, ticks: 30, desc: '~60 Min, maximal' },
    { label: 'Großfeld', icon: 'pi-th-large', personas: 200, ticks: 20, desc: '~90 Min, breit' },
    { label: 'Repräsentativ', icon: 'pi-users', personas: 500, ticks: 30, desc: '~3 Std, Studien-Niveau' },
  ];

  selectedPreset = signal('Standard');

  // Multi-Provider Config (Advanced)
  useProviderConfig = signal(false);
  providerPresets = signal<Preset[]>([]);
  selectedProviderPreset = signal<string | null>(null);
  liveCostEstimate = signal<CostEstimate | null>(null);
  costLoading = signal(false);

  personaGenEntries = signal<PhaseProviderEntry[]>([]);
  agentActionEntries = signal<PhaseProviderEntry[]>([]);
  stateUpdateEntries = signal<PhaseProviderEntry[]>([]);
  analysisEntries = signal<PhaseProviderEntry[]>([]);

  applyPreset(preset: typeof this.presets[0]) {
    this.selectedPreset.set(preset.label);
    this.personaCount.set(preset.personas);
    this.tickCount.set(preset.ticks);
  }

  loadProviderPresets() {
    this.providerService.getPresets().subscribe(presets => this.providerPresets.set(presets));
  }

  toggleProviderConfig() {
    const next = !this.useProviderConfig();
    this.useProviderConfig.set(next);
    if (next) {
      if (this.providerPresets().length === 0) this.loadProviderPresets();
      if (this.availableProviders().length === 0) {
        this.providerService.list().subscribe(p => this.availableProviders.set(p));
      }
    }
  }

  applyProviderPreset(preset: Preset) {
    this.selectedProviderPreset.set(preset.id);

    // Modell-Mapping: tier → konkretes Modell je Provider
    const resolveModel = (tier: string, providerId: string): string => {
      const provider = this.availableProviders().find(p => p.id === providerId);
      const type = provider?.provider_type || 'openai';
      const models = this.modelOptions[type as LlmProvider] || [];
      const match = models.find(m => m.tier === tier);
      return match?.id || models[0]?.id || 'gpt-5-mini';
    };

    const buildEntry = (phase: { model_tier: string; temperature: number }): PhaseProviderEntry => {
      const providers = this.availableProviders();
      const defaultP = providers.find(p => p.is_default) || providers[0];
      if (!defaultP) return { provider_id: '', model: '', weight: 100, temperature: phase.temperature, top_p: null, top_k: null };
      return {
        provider_id: defaultP.id,
        model: resolveModel(phase.model_tier, defaultP.id),
        weight: 100,
        temperature: phase.temperature,
        top_p: null,
        top_k: null,
      };
    };

    this.personaGenEntries.set([buildEntry(preset.persona_generation)]);
    this.agentActionEntries.set([buildEntry(preset.agent_actions)]);
    this.stateUpdateEntries.set([buildEntry(preset.state_updates)]);
    this.analysisEntries.set([buildEntry(preset.analysis_reports)]);
    this.updateCostEstimate();
  }

  availableProviders = signal<Provider[]>([]);

  onPhaseEntriesChange(phase: string, entries: PhaseProviderEntry[]) {
    switch (phase) {
      case 'persona_generation': this.personaGenEntries.set(entries); break;
      case 'agent_actions': this.agentActionEntries.set(entries); break;
      case 'state_updates': this.stateUpdateEntries.set(entries); break;
      case 'analysis_reports': this.analysisEntries.set(entries); break;
    }
    this.updateCostEstimate();
  }

  private costDebounce: ReturnType<typeof setTimeout> | null = null;

  updateCostEstimate() {
    if (this.costDebounce) clearTimeout(this.costDebounce);
    this.costDebounce = setTimeout(() => {
      const config = this.buildProviderConfig();
      if (!config) return;
      this.costLoading.set(true);
      this.providerService.estimateCost({
        persona_count: this.personaCount(),
        tick_count: this.tickCount(),
        provider_config: config,
      }).subscribe({
        next: (est) => { this.liveCostEstimate.set(est); this.costLoading.set(false); },
        error: () => this.costLoading.set(false),
      });
    }, 500);
  }

  buildProviderConfig(): SimulationProviderConfig | null {
    const pg = this.personaGenEntries();
    const aa = this.agentActionEntries();
    const su = this.stateUpdateEntries();
    const ar = this.analysisEntries();
    if (!pg.length || !aa.length || !su.length || !ar.length) return null;
    return {
      persona_generation: { entries: pg },
      agent_actions: { entries: aa },
      state_updates: { entries: su },
      analysis_reports: { entries: ar },
      preset: this.selectedProviderPreset(),
    };
  }

  /** Personas-Slider: bis 100 in 5er-Schritten, ab 100 in 25er-Schritten. */
  setPersonaCount(raw: number) {
    let v = Number(raw);
    if (v > 100) {
      v = Math.round(v / 25) * 25;
    } else {
      v = Math.round(v / 5) * 5;
    }
    this.personaCount.set(v);
    this.selectedPreset.set('');
  }

  setTickCount(raw: number) {
    this.tickCount.set(Number(raw));
    this.selectedPreset.set('');
  }

  nextStep() { if (this.currentStep() < 3) this.currentStep.update(s => s + 1); }
  prevStep() { if (this.currentStep() > 1) this.currentStep.update(s => s - 1); }

  canProceed(): boolean {
    return this.name().trim().length > 0 && this.productDescription().trim().length > 10;
  }

  /** API-Kosten geschätzt auf Basis von Token-Verbrauch und aktuellen Preisen. */
  estimatedCost(): string {
    const p = this.llmProvider();
    // Preise pro 1M Tokens: [input, output]
    const prices: Record<string, { fast: [number, number]; smart: [number, number] }> = {
      anthropic: { fast: [1.00, 5.00], smart: [3.00, 15.00] },
      openai:    { fast: [0.75, 4.50], smart: [2.50, 15.00] },
      ollama:    { fast: [0, 0],       smart: [0, 0] },
    };
    const pr = prices[p] || prices['openai'];
    const personas = this.personaCount();
    const ticks = this.tickCount();

    // Persona-Gen: ~800 input + 350 output tokens pro Persona (smart)
    const genCost = personas * (800 * pr.smart[0] + 350 * pr.smart[1]) / 1_000_000;
    // Tick-Aktionen: ~600 input + 200 output pro Persona*Tick (fast)
    const actionCost = personas * ticks * (600 * pr.fast[0] + 200 * pr.fast[1]) / 1_000_000;
    // State-Updates: ~400 input + 100 output pro Persona*Tick (fast)
    const stateCost = personas * ticks * (400 * pr.fast[0] + 100 * pr.fast[1]) / 1_000_000;
    // Report: ~8000 input + 4000 output (smart, einmalig)
    const reportCost = (8000 * pr.smart[0] + 4000 * pr.smart[1]) / 1_000_000;

    return (genCost + actionCost + stateCost + reportCost).toFixed(2);
  }

  estimatedMinutes(): number {
    // Parallelisiert: ~180 Persona-Aktionen pro Minute realistisch.
    const actionMinutes = Math.ceil(this.personaCount() * this.tickCount() / 180);
    // Persona-Gen: ~25 pro Batch, 4 parallel, ~25s pro Batch.
    const genMinutes = Math.ceil(this.personaCount() / (25 * 4) * 0.5);
    return Math.max(2, actionMinutes + genMinutes + 1);
  }

  /** Warnt ab Sims, die voraussichtlich >60 Min laufen. */
  isLongRun(): boolean {
    return this.estimatedMinutes() >= 60;
  }

  durationLabel(): string {
    const m = this.estimatedMinutes();
    if (m < 60) return `~${m} Min`;
    const h = Math.floor(m / 60);
    const rest = m % 60;
    return rest === 0 ? `~${h} Std` : `~${h} Std ${rest} Min`;
  }

  /** Resolved model_fast für den Create-Payload (oder null = Default). */
  resolveModelFast(): string | null {
    const mode = this.modelMode();
    if (mode === 'standard') return null;
    if (mode === 'premium') {
      // Premium: Smart-Modell auch für Fast-Slot
      return this.smartModelOptions()[0]?.id ?? null;
    }
    // custom
    return this.customModelFast() || null;
  }

  resolveModelSmart(): string | null {
    const mode = this.modelMode();
    if (mode === 'standard') return null;
    if (mode === 'premium') return this.smartModelOptions()[0]?.id ?? null;
    return this.customModelSmart() || null;
  }

  submit() {
    this.submitting.set(true);
    const data: SimulationCreate = {
      name: this.name(),
      product_description: this.productDescription(),
      target_market: this.targetMarket() || undefined,
      industry: this.industry() || undefined,
      config: { persona_count: this.personaCount(), tick_count: this.tickCount() },
      llm_provider: this.llmProvider(),
      llm_model_fast: this.resolveModelFast(),
      llm_model_smart: this.resolveModelSmart(),
    };
    if (this.useProviderConfig()) {
      data.provider_config = this.buildProviderConfig();
    }
    this.simService.create(data).subscribe({
      next: (sim) => {
        this.simService.run(sim.id).subscribe({
          next: () => this.router.navigate(['/simulation', sim.id, 'overview']),
          error: () => this.router.navigate(['/simulation', sim.id, 'overview']),
        });
      },
      error: () => this.submitting.set(false),
    });
  }
}
