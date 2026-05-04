import { Component, inject, signal, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { TriggerEventService } from '../../../core/services/trigger-event.service';
import { TriggerEvent, TriggerEventCreate, TriggerEventType, TriggerIntensity } from '../../../core/models/trigger-event.model';
import { TemplateService } from '../../../core/services/template.service';
import { Template } from '../../../core/models/template.model';

@Component({
  selector: 'app-triggers',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './triggers.component.html',
})
export class TriggersComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private triggerService = inject(TriggerEventService);
  private templateService = inject(TemplateService);

  simulationId = '';
  events = signal<TriggerEvent[]>([]);
  loading = signal(true);
  showDialog = signal(false);
  triggerTemplates = signal<Template[]>([]);

  // Form
  newTitle = signal('');
  newContent = signal('');
  newTickDay = signal(1);
  newEventType = signal<TriggerEventType>('news_headline');
  newIntensity = signal<TriggerIntensity>('minor');
  newAffectedSegments = signal('');

  eventTypes: { id: TriggerEventType; label: string }[] = [
    { id: 'news_headline', label: 'Nachricht/Schlagzeile' },
    { id: 'competitor_action', label: 'Wettbewerber-Aktion' },
    { id: 'regulatory_change', label: 'Regulatorische Aenderung' },
    { id: 'validator_decision', label: 'Validierer-Entscheidung' },
    { id: 'social_incident', label: 'Sozialer Vorfall' },
  ];

  intensities: { id: TriggerIntensity; label: string }[] = [
    { id: 'minor', label: 'Gering' },
    { id: 'major', label: 'Mittel' },
    { id: 'critical', label: 'Kritisch' },
  ];

  ngOnInit() {
    this.simulationId = this.route.parent?.snapshot.paramMap.get('id') || '';
    this.loadEvents();
    this.templateService.list({ category: 'trigger_library' }).subscribe({
      next: res => this.triggerTemplates.set(res.items),
    });
  }

  loadEvents() {
    this.loading.set(true);
    this.triggerService.list(this.simulationId).subscribe({
      next: events => { this.events.set(events); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  openDialog() { this.showDialog.set(true); }
  closeDialog() { this.showDialog.set(false); this.resetForm(); }

  resetForm() {
    this.newTitle.set('');
    this.newContent.set('');
    this.newTickDay.set(1);
    this.newEventType.set('news_headline');
    this.newIntensity.set('minor');
    this.newAffectedSegments.set('');
  }

  applyTemplate(tmpl: Template) {
    this.newTitle.set(tmpl.name);
    this.newContent.set(tmpl.content['content'] || '');
    this.newEventType.set((tmpl.content['event_type'] as TriggerEventType) || 'news_headline');
    this.newIntensity.set((tmpl.content['intensity'] as TriggerIntensity) || 'minor');
    this.newAffectedSegments.set((tmpl.content['affected_segments'] || []).join(', '));
  }

  createEvent() {
    const segments = this.newAffectedSegments().split(',').map(s => s.trim()).filter(Boolean);
    const data: TriggerEventCreate = {
      simulation_id: this.simulationId,
      tick_day: this.newTickDay(),
      event_type: this.newEventType(),
      title: this.newTitle(),
      content: this.newContent() || undefined,
      affected_segments: segments,
      intensity: this.newIntensity(),
    };
    this.triggerService.create(data).subscribe({
      next: () => { this.closeDialog(); this.loadEvents(); },
    });
  }

  deleteEvent(id: string) {
    this.triggerService.delete(id).subscribe(() => this.loadEvents());
  }

  getIntensityBadge(intensity: string): string {
    switch (intensity) {
      case 'critical': return 'badge-danger';
      case 'major': return 'badge-warning';
      default: return 'badge-info';
    }
  }

  getEventTypeLabel(type: string): string {
    return this.eventTypes.find(e => e.id === type)?.label || type;
  }
}
