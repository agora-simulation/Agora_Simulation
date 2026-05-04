import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { DatePipe } from '@angular/common';
import { ResearchSnapshotService } from '../../core/services/research-snapshot.service';
import { ProviderService } from '../../core/services/provider.service';
import { TemplateService } from '../../core/services/template.service';
import { ResearchSnapshot } from '../../core/models/research-snapshot.model';
import { Provider, ProviderCapabilities, ModelCapabilities } from '../../core/models/provider.model';
import { Template } from '../../core/models/template.model';
import { MarkdownPipe } from '../../shared/pipes/markdown.pipe';

@Component({
  selector: 'app-research-detail',
  standalone: true,
  imports: [FormsModule, RouterLink, DatePipe, MarkdownPipe],
  templateUrl: './research-detail.component.html',
})
export class ResearchDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private researchService = inject(ResearchSnapshotService);
  private providerService = inject(ProviderService);
  private templateService = inject(TemplateService);

  snapshot = signal<ResearchSnapshot | null>(null);
  providers = signal<Provider[]>([]);
  capabilities = signal<ProviderCapabilities[]>([]);
  templates = signal<Template[]>([]);
  loading = signal(true);
  executing = signal(false);
  saving = signal(false);

  // Form fields
  name = signal('');
  selectedProviderId = signal<string | null>(null);
  selectedModel = signal<string | null>(null);
  prompt = signal('');
  systemPrompt = signal('');
  temperature = signal<number | null>(null);
  maxTokens = signal(4096);
  selectedTemplateId = signal<string | null>(null);
  showSystemPrompt = signal(false);

  // Computed: available models for selected provider
  availableModels = computed(() => {
    const providerId = this.selectedProviderId();
    const provider = this.providers().find(p => p.id === providerId);
    if (!provider) return [];
    const caps = this.capabilities().find(c => c.provider_type === provider.provider_type);
    return caps?.models || [];
  });

  selectedProviderType = computed(() => {
    const providerId = this.selectedProviderId();
    return this.providers().find(p => p.id === providerId)?.provider_type || null;
  });

  ngOnInit() {
    const id = this.route.snapshot.paramMap.get('id');
    if (!id) { this.router.navigate(['/research']); return; }

    // Load all data in parallel
    this.researchService.getById(id).subscribe({
      next: snap => {
        this.snapshot.set(snap);
        this.name.set(snap.name);
        this.selectedProviderId.set(snap.provider_id);
        this.selectedModel.set(snap.model);
        this.prompt.set(snap.prompt || '');
        this.systemPrompt.set(snap.system_prompt || '');
        this.temperature.set(snap.temperature);
        this.maxTokens.set(snap.max_tokens || 4096);
        this.selectedTemplateId.set(snap.template_id);
        this.loading.set(false);
      },
      error: () => { this.router.navigate(['/research']); },
    });

    this.providerService.list().subscribe(p => this.providers.set(p));
    this.providerService.getCapabilities().subscribe(c => this.capabilities.set(c));
    this.templateService.list({ category: 'research' }).subscribe(t => this.templates.set(t.items));
  }

  onProviderChange(providerId: string) {
    this.selectedProviderId.set(providerId);
    // Auto-select first smart model
    const models = this.availableModels();
    const smart = models.find(m => m.tier === 'smart') || models[0];
    this.selectedModel.set(smart?.model_id || null);
  }

  onTemplateSelect(templateId: string) {
    this.selectedTemplateId.set(templateId || null);
    if (!templateId) return;
    const tmpl = this.templates().find(t => t.id === templateId);
    if (tmpl?.content) {
      if (tmpl.content['prompt']) this.prompt.set(tmpl.content['prompt']);
      if (tmpl.content['system_prompt']) {
        this.systemPrompt.set(tmpl.content['system_prompt']);
        this.showSystemPrompt.set(true);
      }
    }
  }

  saveConfig() {
    const snap = this.snapshot();
    if (!snap) return;
    this.saving.set(true);
    this.researchService.update(snap.id, {
      name: this.name(),
      provider_id: this.selectedProviderId(),
      model: this.selectedModel(),
      prompt: this.prompt(),
      system_prompt: this.systemPrompt() || null,
      template_id: this.selectedTemplateId(),
      temperature: this.temperature(),
      max_tokens: this.maxTokens(),
    } as any).subscribe({
      next: updated => { this.snapshot.set(updated); this.saving.set(false); },
      error: () => this.saving.set(false),
    });
  }

  execute() {
    const snap = this.snapshot();
    if (!snap) return;
    this.executing.set(true);
    this.researchService.execute(snap.id, {
      prompt: this.prompt(),
      system_prompt: this.systemPrompt() || undefined,
      provider_id: this.selectedProviderId() || undefined,
      model: this.selectedModel() || undefined,
      temperature: this.temperature() ?? undefined,
      max_tokens: this.maxTokens(),
    }).subscribe({
      next: updated => {
        this.snapshot.set(updated);
        this.executing.set(false);
      },
      error: () => this.executing.set(false),
    });
  }

  approve() {
    const snap = this.snapshot();
    if (!snap) return;
    this.researchService.approve(snap.id).subscribe(updated => this.snapshot.set(updated));
  }

  statusBadgeClass(status: string): string {
    switch (status) {
      case 'completed': return 'badge-success';
      case 'approved': return 'badge-primary';
      case 'running': return 'badge-warning';
      case 'failed': return 'badge-danger';
      case 'archived': return 'badge-muted';
      default: return 'badge-info';
    }
  }

  statusLabel(status: string): string {
    const map: Record<string, string> = {
      draft: 'Entwurf', running: 'Laeuft...', completed: 'Abgeschlossen',
      approved: 'Freigegeben', archived: 'Archiviert', failed: 'Fehlgeschlagen',
    };
    return map[status] || status;
  }

  executionDuration(): string | null {
    const snap = this.snapshot();
    if (!snap?.execution_started_at || !snap?.execution_finished_at) return null;
    const ms = new Date(snap.execution_finished_at).getTime() - new Date(snap.execution_started_at).getTime();
    return (ms / 1000).toFixed(1) + 's';
  }
}
