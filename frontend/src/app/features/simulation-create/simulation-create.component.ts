import { Component, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { SimulationService } from '../../core/services/simulation.service';
import { ProviderService } from '../../core/services/provider.service';
import { SimulationCreate, LlmProvider, ResearchMode } from '../../core/models/simulation.model';
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
  researchMode = signal<ResearchMode>('quick');

  readonly providers: { id: LlmProvider; label: string; sub: string; icon: string }[] = [
    { id: 'anthropic', label: 'Claude (Anthropic)', sub: 'Sonnet 4.6 + Haiku 4.5', icon: 'pi-sparkles' },
    { id: 'openai',    label: 'OpenAI',             sub: 'GPT-5 + GPT-5-mini',     icon: 'pi-bolt' },
  ];

  // Modell-Wahl
  customModelFast = signal<string>('');
  customModelSmart = signal<string>('');
  showAdvanced = signal(false);

  // Modell-Optionen pro Provider mit Beschreibung
  readonly modelOptions: Record<LlmProvider, { id: string; label: string; tier: 'fast' | 'smart'; info: string }[]> = {
    anthropic: [
      { id: 'claude-haiku-4-5-20251001', label: 'Claude Haiku 4.5',   tier: 'fast',  info: 'Sehr schnell & g\u00FCnstig. Ideal f\u00FCr Massen-Aktionen (Posts, Reaktionen). $1/M Input.' },
      { id: 'claude-sonnet-4-6',         label: 'Claude Sonnet 4.6',  tier: 'smart', info: 'Bestes Preis-Leistungs-Verh\u00E4ltnis. Empfohlen f\u00FCr Persona-Generierung & Reports. $3/M Input.' },
      { id: 'claude-sonnet-4-5',         label: 'Claude Sonnet 4.5',  tier: 'smart', info: 'Vorg\u00E4nger von 4.6, etwas g\u00FCnstiger. Solide Alternative.' },
      { id: 'claude-opus-4-6',           label: 'Claude Opus 4.6',    tier: 'smart', info: 'Top-Qualit\u00E4t, teuer. F\u00FCr maximale Persona-Koh\u00E4renz & tiefgehende Reports. $15/M Input.' },
    ],
    openai: [
      { id: 'gpt-4.1-mini',  label: 'GPT-4.1-mini',  tier: 'fast',  info: 'Schnell & sehr g\u00FCnstig. Gut f\u00FCr Massen-Aktionen. $0.40/M Input.' },
      { id: 'gpt-4.1-nano',  label: 'GPT-4.1-nano',  tier: 'fast',  info: 'Schnellstes & g\u00FCnstigstes OpenAI-Modell. F\u00FCr einfache Aktionen. $0.10/M Input.' },
      { id: 'gpt-5-mini',    label: 'GPT-5-mini',     tier: 'fast',  info: 'Neueste Generation, hohe TPM-Limits. Ideal bei vielen Personas (200+). $0.75/M Input.' },
      { id: 'gpt-4o',        label: 'GPT-4o',         tier: 'smart', info: 'Ausgewogen, bew\u00E4hrt. Gute Persona-Qualit\u00E4t zu moderatem Preis. $2.50/M Input.' },
      { id: 'gpt-4.1',       label: 'GPT-4.1',        tier: 'smart', info: 'Stark bei Instruktionstreue & langen Kontexten. Gut f\u00FCr Reports. $2/M Input.' },
      { id: 'gpt-5',         label: 'GPT-5',           tier: 'smart', info: 'Neueste Generation, Top-Qualit\u00E4t. Maximale Persona-Koh\u00E4renz. $2.50/M Input.' },
      { id: 'o3-mini',       label: 'o3-mini',         tier: 'smart', info: 'Reasoning-Modell. Langsamer, aber sehr analytisch. Ideal f\u00FCr Analyse-Reports. $1.10/M Input.' },
    ],
    ollama: [
      { id: 'qwen2.5:7b',    label: 'Qwen 2.5 7B',    tier: 'fast',  info: 'Lokales Fast-Modell. Keine API-Kosten, moderate Qualit\u00E4t.' },
      { id: 'qwen2.5:32b',   label: 'Qwen 2.5 32B',   tier: 'smart', info: 'Lokales Qualit\u00E4tsmodell. Braucht 24 GB VRAM.' },
      { id: 'llama3.1:8b',   label: 'Llama 3.1 8B',    tier: 'fast',  info: 'Meta Llama, solide Grundqualit\u00E4t. 8 GB VRAM.' },
      { id: 'llama3.1:70b',  label: 'Llama 3.1 70B',   tier: 'smart', info: 'Sehr gute Qualit\u00E4t, braucht 48 GB VRAM.' },
    ],
  };

  /** Aktuelle Modell-Optionen f\u00FCr Fast-Tier abh\u00E4ngig vom Provider. */
  fastModelOptions() {
    return this.modelOptions[this.llmProvider()].filter(m => m.tier === 'fast');
  }
  smartModelOptions() {
    return this.modelOptions[this.llmProvider()].filter(m => m.tier === 'smart');
  }
  allModelOptions() {
    return this.modelOptions[this.llmProvider()];
  }

  // Beispiel-Szenarien als klickbare Templates
  readonly templates = [
    {
      label: 'Produktlaunch',
      icon: 'pi-car',
      name: 'E-Auto Launch DACH',
      desc: 'Ein autonomer E-Transporter mit 50 kWh Batterie, der per App bestellt wird. Preis ab 78.000 \u20AC, Leasing ab 1.290 \u20AC/Monat. Zielgruppen: Flottenbetreiber, Hotels, Parkh\u00E4user.',
      market: 'DACH, B2B & B2C',
      industry: 'Automobil / E-Mobilit\u00E4t',
    },
    {
      label: 'Kampagne',
      icon: 'pi-megaphone',
      name: 'Gen-Z Finanz-App Kampagne',
      desc: 'Eine Banking-App f\u00FCr 18-25-J\u00E4hrige mit Spar-Challenges, Social Features und Krypto-Integration. Freemium-Modell, Premium ab 4,99 \u20AC/Monat.',
      market: 'Deutschland, 18\u201325 Jahre',
      industry: 'FinTech',
    },
    {
      label: 'Preis\u00E4nderung',
      icon: 'pi-tag',
      name: 'SaaS Pricing Relaunch',
      desc: 'Ein B2B-Projektmanagement-Tool erh\u00F6ht die Preise um 40 %. Neues Tier-Modell: Free, Pro (29 \u20AC), Enterprise (99 \u20AC). Bestehende Kunden bekommen 12 Monate Bestandsschutz.',
      market: 'Europa, B2B',
      industry: 'SaaS / Software',
    },
  ];

  selectedTemplate = signal<string | null>(null);

  applyTemplate(t: typeof this.templates[0]) {
    this.selectedTemplate.set(t.label);
    this.name.set(t.name);
    this.productDescription.set(t.desc);
    this.targetMarket.set(t.market);
    this.industry.set(t.industry);
  }

  clearTemplate() {
    this.selectedTemplate.set(null);
    this.name.set('');
    this.productDescription.set('');
    this.targetMarket.set('');
    this.industry.set('');
  }

  // Presets
  readonly presets = [
    { label: 'Schnelltest', icon: 'pi-bolt', personas: 10, ticks: 5, desc: 'Schnelle Stimmungspr\u00FCfung f\u00FCr erste Hypothesen', stats: '10 Personas \u00B7 5 Tage \u00B7 ~2 Min' },
    { label: 'Standard', icon: 'pi-chart-bar', personas: 30, ticks: 15, desc: 'Solide Analyse mit breitem Meinungsspektrum', stats: '30 Personas \u00B7 15 Tage \u00B7 ~8 Min' },
    { label: 'Deep Dive', icon: 'pi-search', personas: 50, ticks: 20, desc: 'Tiefe Meinungsentwicklung mit Narrative-Tracking', stats: '50 Personas \u00B7 20 Tage \u00B7 ~20 Min' },
    { label: 'Enterprise', icon: 'pi-building', personas: 100, ticks: 30, desc: 'Vollst\u00E4ndige Marktsimulation mit statistischer Belastbarkeit', stats: '100 Personas \u00B7 30 Tage \u00B7 ~1 Std' },
    { label: 'Gro\u00DFfeld', icon: 'pi-th-large', personas: 200, ticks: 20, desc: 'Breites Meinungsbild, ideal f\u00FCr segmentierte Zielgruppen', stats: '200 Personas \u00B7 20 Tage \u00B7 ~1.5 Std' },
    { label: 'Repr\u00E4sentativ', icon: 'pi-users', personas: 500, ticks: 30, desc: 'Studien-Niveau mit voller Meinungsvielfalt', stats: '500 Personas \u00B7 30 Tage \u00B7 ~3 Std' },
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

  /** API-Kosten geschätzt auf Basis von Token-Verbrauch und aktuellen Preisen.
   *  Aktualisiert für Hybrid-Persona-Generierung + MarketContext + erweiterte Prompts. */
  estimatedCost(): string {
    const p = this.llmProvider();
    const prices: Record<string, { fast: [number, number]; smart: [number, number] }> = {
      anthropic: { fast: [1.00, 5.00], smart: [3.00, 15.00] },
      openai:    { fast: [0.75, 4.50], smart: [2.50, 15.00] },
      ollama:    { fast: [0, 0],       smart: [0, 0] },
    };
    const pr = prices[p] || prices['openai'];
    const personas = this.personaCount();
    const ticks = this.tickCount();
    const isDeep = this.researchMode() === 'deep';

    // Persona-Gen (Hybrid): 2 Smart-Calls pro Persona (Skelett ~800+500 + Enrichment ~1500+800)
    const genCost = personas * (2500 * pr.smart[0] + 1500 * pr.smart[1]) / 1_000_000;
    // Tick-Aktionen: ~1200 input + 400 output pro Persona*Tick (fast, mit MarketContext)
    const actionCost = personas * ticks * (1200 * pr.fast[0] + 400 * pr.fast[1]) / 1_000_000;
    // State-Updates: ~800 input + 300 output pro Persona*Tick (fast)
    const stateCost = personas * ticks * (800 * pr.fast[0] + 300 * pr.fast[1]) / 1_000_000;
    // Report: ~30000 input + 12000 output (smart, mit allen Posts + MarketContext)
    const reportCost = (30000 * pr.smart[0] + 12000 * pr.smart[1]) / 1_000_000;
    // Deep Mode: Recherche (~3 Calls Smart, ~5000 input + 3000 output)
    const researchCost = isDeep ? (5000 * pr.smart[0] + 3000 * pr.smart[1]) / 1_000_000 : 0;

    return (genCost + actionCost + stateCost + reportCost + researchCost).toFixed(2);
  }

  estimatedMinutes(): number {
    const personas = this.personaCount();
    const ticks = this.tickCount();
    const isDeep = this.researchMode() === 'deep';

    // Persona-Gen (Hybrid): Skelett-Batches (3er, 10 parallel) + Enrichment (10 parallel)
    // ~3s pro Skelett-Batch, ~4s pro Enrichment-Call
    const skeletonBatches = Math.ceil(personas / 3);
    const skeletonMinutes = Math.ceil(skeletonBatches / 10 * 3 / 60);
    const enrichMinutes = Math.ceil(personas / 10 * 4 / 60);
    const genMinutes = skeletonMinutes + enrichMinutes;

    // Tick-Loop: Pro Tick 2 Phasen (Actions + State), je ~5-8s pro Call, 10 parallel
    // GPT-5 ist langsam (~6s pro Call), Actions + State = 2 Runden pro Persona
    const secondsPerTick = Math.ceil(personas / 10 * 6 * 2);
    const tickMinutes = Math.ceil(ticks * secondsPerTick / 60);

    // Deep Mode: Recherche (~5 Min) + Review-Pause (nicht gezählt)
    const researchMinutes = isDeep ? 5 : 0;

    // Report: ~3-5 Min
    const reportMinutes = 4;

    return Math.max(3, genMinutes + tickMinutes + researchMinutes + reportMinutes);
  }

  /** Warnt ab Sims, die voraussichtlich >60 Min laufen. */
  isLongRun(): boolean {
    return this.estimatedMinutes() >= 30;
  }

  durationLabel(): string {
    const m = this.estimatedMinutes();
    if (m < 60) return `~${m} Min`;
    const h = Math.floor(m / 60);
    const rest = m % 60;
    return rest === 0 ? `~${h} Std` : `~${h} Std ${rest} Min`;
  }

  /** Resolved model_fast für den Create-Payload (oder null = Provider-Default). */
  resolveModelFast(): string | null {
    return this.customModelFast() || null;
  }

  resolveModelSmart(): string | null {
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
      research_mode: this.researchMode(),
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
