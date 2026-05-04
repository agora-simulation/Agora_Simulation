import { Component, inject, signal, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { KeyValuePipe } from '@angular/common';
import { TemplateService } from '../../core/services/template.service';
import { Template, TemplateCategory } from '../../core/models/template.model';
import { CardGlowDirective } from '../../shared/directives/card-glow.directive';

@Component({
  selector: 'app-templates',
  standalone: true,
  imports: [FormsModule, KeyValuePipe, CardGlowDirective],
  templateUrl: './templates.component.html',
  host: { 'style': 'display: block; position: static;' },
})
export class TemplatesComponent implements OnInit {
  private templateService = inject(TemplateService);

  templates = signal<Template[]>([]);
  loading = signal(true);
  activeCategory = signal<TemplateCategory>('distribution');
  showCreateDialog = signal(false);
  showEditDialog = signal(false);
  saving = signal(false);

  categories: { id: TemplateCategory; label: string; icon: string; hint: string }[] = [
    { id: 'distribution', label: 'Akteurs-Verteilung', icon: 'pi-chart-pie', hint: 'Prozentuale Verteilung der Akteur-Typen in Simulationen (B2C, B2B, Politik usw.)' },
    { id: 'tonality', label: 'Tonalitaet', icon: 'pi-comment', hint: 'Sprachstil und Tonalitaet pro Akteur-Typ' },
    { id: 'trigger_library', label: 'Trigger-Library', icon: 'pi-bolt', hint: 'Vorgefertigte Trigger-Events zum Injizieren' },
  ];

  // Actor types for distribution sliders
  readonly actorTypes = [
    { key: 'private_person', label: 'Privatperson' },
    { key: 'company', label: 'Unternehmen' },
    { key: 'research_institute', label: 'Forschungsinstitut' },
    { key: 'authority', label: 'Behoerde' },
    { key: 'media', label: 'Medien' },
    { key: 'influencer', label: 'Influencer' },
    { key: 'expert', label: 'Experte' },
    { key: 'collective', label: 'Kollektiv/Verband' },
    { key: 'validator', label: 'Validierer' },
  ];

  readonly eventTypes = [
    { id: 'news_headline', label: 'Nachricht/Schlagzeile' },
    { id: 'competitor_action', label: 'Wettbewerber-Aktion' },
    { id: 'regulatory_change', label: 'Regulatorische Aenderung' },
    { id: 'validator_decision', label: 'Validierer-Entscheidung' },
    { id: 'social_incident', label: 'Sozialer Vorfall' },
  ];

  readonly intensities = [
    { id: 'minor', label: 'Gering' },
    { id: 'major', label: 'Mittel' },
    { id: 'critical', label: 'Kritisch' },
  ];

  // Create form signals
  newName = signal('');
  // Distribution
  newDist = signal<Record<string, number>>({});
  // Tonality
  newTonalityText = signal('');
  // Trigger
  newTriggerEventType = signal('news_headline');
  newTriggerIntensity = signal('minor');
  newTriggerContent = signal('');
  newTriggerSegments = signal('');

  // Edit form signals
  editId = signal('');
  editName = signal('');
  editDist = signal<Record<string, number>>({});
  editTonalityText = signal('');
  editTriggerEventType = signal('news_headline');
  editTriggerIntensity = signal('minor');
  editTriggerContent = signal('');
  editTriggerSegments = signal('');

  ngOnInit() { this.load(); }

  load() {
    this.loading.set(true);
    this.templateService.list({ category: this.activeCategory() }).subscribe({
      next: res => { this.templates.set(res.items); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  switchCategory(cat: TemplateCategory) {
    this.activeCategory.set(cat);
    this.load();
  }

  seedDefaults() {
    this.templateService.seedDefaults().subscribe(() => this.load());
  }

  // --- Create ---
  openCreateDialog() {
    this.newName.set('');
    const emptyDist: Record<string, number> = {};
    this.actorTypes.forEach(a => emptyDist[a.key] = 0);
    this.newDist.set(emptyDist);
    this.newTonalityText.set('');
    this.newTriggerEventType.set('news_headline');
    this.newTriggerIntensity.set('minor');
    this.newTriggerContent.set('');
    this.newTriggerSegments.set('');
    this.showCreateDialog.set(true);
  }

  setNewDist(key: string, value: number) {
    this.newDist.update(d => ({ ...d, [key]: value }));
  }

  createTemplate() {
    this.saving.set(true);
    const cat = this.activeCategory();
    let content: Record<string, any> = {};

    if (cat === 'distribution') {
      content = { ...this.newDist() };
    } else if (cat === 'tonality') {
      content = { text: this.newTonalityText() };
    } else if (cat === 'trigger_library') {
      const segments = this.newTriggerSegments().split(',').map(s => s.trim()).filter(Boolean);
      content = {
        event_type: this.newTriggerEventType(),
        intensity: this.newTriggerIntensity(),
        content: this.newTriggerContent(),
        affected_segments: segments,
      };
    }

    this.templateService.create({ category: cat, name: this.newName(), content }).subscribe({
      next: () => { this.showCreateDialog.set(false); this.saving.set(false); this.load(); },
      error: () => this.saving.set(false),
    });
  }

  canCreate(): boolean {
    if (!this.newName()) return false;
    const cat = this.activeCategory();
    if (cat === 'tonality') return !!this.newTonalityText();
    if (cat === 'trigger_library') return !!this.newTriggerContent();
    return true;
  }

  // --- Edit ---
  openEditDialog(t: Template) {
    this.editId.set(t.id);
    this.editName.set(t.name);

    if (this.activeCategory() === 'distribution') {
      const dist: Record<string, number> = {};
      this.actorTypes.forEach(a => dist[a.key] = t.content[a.key] ?? 0);
      this.editDist.set(dist);
    } else if (this.activeCategory() === 'tonality') {
      this.editTonalityText.set(t.content['text'] || '');
    } else if (this.activeCategory() === 'trigger_library') {
      this.editTriggerEventType.set(t.content['event_type'] || 'news_headline');
      this.editTriggerIntensity.set(t.content['intensity'] || 'minor');
      this.editTriggerContent.set(t.content['content'] || '');
      this.editTriggerSegments.set((t.content['affected_segments'] || []).join(', '));
    }
    this.showEditDialog.set(true);
  }

  setEditDist(key: string, value: number) {
    this.editDist.update(d => ({ ...d, [key]: value }));
  }

  updateTemplate() {
    this.saving.set(true);
    const cat = this.activeCategory();
    let content: Record<string, any> = {};

    if (cat === 'distribution') {
      content = { ...this.editDist() };
    } else if (cat === 'tonality') {
      content = { text: this.editTonalityText() };
    } else if (cat === 'trigger_library') {
      const segments = this.editTriggerSegments().split(',').map(s => s.trim()).filter(Boolean);
      content = {
        event_type: this.editTriggerEventType(),
        intensity: this.editTriggerIntensity(),
        content: this.editTriggerContent(),
        affected_segments: segments,
      };
    }

    this.templateService.update(this.editId(), { name: this.editName(), content }).subscribe({
      next: () => { this.showEditDialog.set(false); this.saving.set(false); this.load(); },
      error: () => this.saving.set(false),
    });
  }

  deleteTemplate(id: string) {
    this.templateService.delete(id).subscribe(() => this.load());
  }

  distSum(dist: Record<string, number>): number {
    return Object.values(dist).reduce((a, b) => a + (b || 0), 0);
  }
}
