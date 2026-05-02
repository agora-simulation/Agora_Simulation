import { Component, inject, signal, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ProviderService } from '../../core/services/provider.service';
import { Provider, ProviderCreate, ProviderType } from '../../core/models/provider.model';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './settings.component.html',
})
export class SettingsComponent implements OnInit {
  private providerService = inject(ProviderService);

  providers = signal<Provider[]>([]);
  loading = signal(true);
  showAddDialog = signal(false);
  showEditDialog = signal(false);
  testingId = signal<string | null>(null);
  testResult = signal<{ success: boolean; message: string } | null>(null);
  testResultFor = signal<string | null>(null);

  // Add Form
  newName = signal('');
  newType = signal<ProviderType>('openai');
  newApiKey = signal('');
  newBaseUrl = signal('');
  newIsDefault = signal(false);
  saving = signal(false);

  // Edit Form
  editId = signal('');
  editName = signal('');
  editApiKey = signal('');
  editBaseUrl = signal('');
  editIsDefault = signal(false);

  providerTypes: { value: ProviderType; label: string }[] = [
    { value: 'anthropic', label: 'Anthropic (Claude)' },
    { value: 'openai', label: 'OpenAI (GPT)' },
    { value: 'ollama', label: 'Ollama (Lokal)' },
  ];

  ngOnInit() {
    this.loadProviders();
  }

  loadProviders() {
    this.loading.set(true);
    this.providerService.list().subscribe({
      next: (providers) => {
        this.providers.set(providers);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  openAddDialog() {
    this.newName.set('');
    this.newType.set('openai');
    this.newApiKey.set('');
    this.newBaseUrl.set('');
    this.newIsDefault.set(false);
    this.showAddDialog.set(true);
  }

  createProvider() {
    this.saving.set(true);
    const data: ProviderCreate = {
      name: this.newName(),
      provider_type: this.newType(),
      api_key: this.newApiKey(),
      is_default: this.newIsDefault(),
    };
    if (this.newType() === 'ollama' && this.newBaseUrl()) {
      data.base_url = this.newBaseUrl();
    }
    this.providerService.create(data).subscribe({
      next: () => {
        this.showAddDialog.set(false);
        this.saving.set(false);
        this.loadProviders();
      },
      error: () => this.saving.set(false),
    });
  }

  openEditDialog(provider: Provider) {
    this.editId.set(provider.id);
    this.editName.set(provider.name);
    this.editApiKey.set('');
    this.editBaseUrl.set(provider.base_url || '');
    this.editIsDefault.set(provider.is_default);
    this.showEditDialog.set(true);
  }

  updateProvider() {
    this.saving.set(true);
    const data: Record<string, unknown> = { name: this.editName(), is_default: this.editIsDefault() };
    if (this.editApiKey()) data['api_key'] = this.editApiKey();
    if (this.editBaseUrl()) data['base_url'] = this.editBaseUrl();

    this.providerService.update(this.editId(), data).subscribe({
      next: () => {
        this.showEditDialog.set(false);
        this.saving.set(false);
        this.loadProviders();
      },
      error: () => this.saving.set(false),
    });
  }

  testProvider(id: string) {
    this.testingId.set(id);
    this.testResult.set(null);
    this.testResultFor.set(id);
    this.providerService.test(id).subscribe({
      next: (result) => {
        this.testResult.set(result);
        this.testingId.set(null);
      },
      error: () => {
        this.testResult.set({ success: false, message: 'Verbindungsfehler' });
        this.testingId.set(null);
      },
    });
  }

  deleteProvider(id: string, name: string) {
    if (confirm(`Provider "${name}" wirklich loeschen?`)) {
      this.providerService.delete(id).subscribe(() => this.loadProviders());
    }
  }

  getTypeLabel(type: string): string {
    return this.providerTypes.find(t => t.value === type)?.label || type;
  }

  getTypeIcon(type: string): string {
    switch (type) {
      case 'anthropic': return 'pi-bolt';
      case 'openai': return 'pi-microchip-ai';
      case 'ollama': return 'pi-server';
      default: return 'pi-cog';
    }
  }
}
