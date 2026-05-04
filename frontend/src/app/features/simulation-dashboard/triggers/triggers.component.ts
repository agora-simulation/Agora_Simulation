import { Component, inject, signal, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { TriggerEventService } from '../../../core/services/trigger-event.service';
import { TriggerEvent, TriggerEventCreate, TriggerEventType, TriggerIntensity } from '../../../core/models/trigger-event.model';

@Component({
  selector: 'app-triggers',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './triggers.component.html',
})
export class TriggersComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private triggerService = inject(TriggerEventService);

  simulationId = '';
  events = signal<TriggerEvent[]>([]);
  loading = signal(true);
  showDialog = signal(false);

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

  intensities: { id: TriggerIntensity; label: string; color: string }[] = [
    { id: 'minor', label: 'Gering', color: 'bg-blue-100 text-blue-800' },
    { id: 'major', label: 'Mittel', color: 'bg-yellow-100 text-yellow-800' },
    { id: 'critical', label: 'Kritisch', color: 'bg-red-100 text-red-800' },
  ];

  ngOnInit() {
    this.simulationId = this.route.parent?.snapshot.paramMap.get('id') || '';
    this.loadEvents();
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

  getIntensityClass(intensity: string): string {
    return this.intensities.find(i => i.id === intensity)?.color || '';
  }

  getEventTypeLabel(type: string): string {
    return this.eventTypes.find(e => e.id === type)?.label || type;
  }
}
