import { Component, inject, signal, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { PlatformService } from '../../core/services/platform.service';
import { SimPlatform } from '../../core/models/platform.model';
import { CardGlowDirective } from '../../shared/directives/card-glow.directive';

@Component({
  selector: 'app-platforms',
  standalone: true,
  imports: [FormsModule, CardGlowDirective],
  templateUrl: './platforms.component.html',
  host: { 'style': 'display: block; position: static;' },
})
export class PlatformsComponent implements OnInit {
  private platformService = inject(PlatformService);

  platforms = signal<SimPlatform[]>([]);
  loading = signal(true);
  showCreateDialog = signal(false);
  showEditDialog = signal(false);
  saving = signal(false);

  readonly characters = [
    { id: 'operativ', label: 'Operativ', desc: 'Schnell, direkt, meinungsstark' },
    { id: 'institutionell', label: 'Institutionell', desc: 'Formell, sachlich, moderiert' },
    { id: 'boulevard', label: 'Boulevard', desc: 'Emotional, polarisierend, viral' },
    { id: 'fachlich', label: 'Fachlich', desc: 'Evidenzbasiert, tiefgehend, nischig' },
    { id: 'oeffentlich', label: 'Oeffentlich', desc: 'Breit, divers, niedrigschwellig' },
  ];

  // Create form
  newName = signal('');
  newCharacter = signal('operativ');
  newReach = signal(1.0);
  newEcho = signal(0.3);
  newEngagement = signal(0.15);
  newTonality = signal('');

  // Edit form
  editId = signal('');
  editName = signal('');
  editCharacter = signal('operativ');
  editReach = signal(1.0);
  editEcho = signal(0.3);
  editEngagement = signal(0.15);
  editTonality = signal('');

  ngOnInit() { this.load(); }

  load() {
    this.loading.set(true);
    this.platformService.list().subscribe({
      next: p => { this.platforms.set(p); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  seedDefaults() {
    this.platformService.seedDefaults().subscribe(() => this.load());
  }

  toggleActive(platform: SimPlatform) {
    this.platformService.update(platform.id, { is_active: !platform.is_active }).subscribe(() => this.load());
  }

  // Create
  openCreateDialog() {
    this.newName.set('');
    this.newCharacter.set('operativ');
    this.newReach.set(1.0);
    this.newEcho.set(0.3);
    this.newEngagement.set(0.15);
    this.newTonality.set('');
    this.showCreateDialog.set(true);
  }

  createPlatform() {
    this.saving.set(true);
    this.platformService.create({
      name: this.newName(),
      character: this.newCharacter(),
      reach_multiplier: this.newReach(),
      echo_chamber_strength: this.newEcho(),
      default_engagement_rate: this.newEngagement(),
      tonality_modifier: this.newTonality() || undefined,
    }).subscribe({
      next: () => { this.showCreateDialog.set(false); this.saving.set(false); this.load(); },
      error: () => this.saving.set(false),
    });
  }

  // Edit
  openEditDialog(p: SimPlatform) {
    this.editId.set(p.id);
    this.editName.set(p.name);
    this.editCharacter.set(p.character);
    this.editReach.set(p.reach_multiplier);
    this.editEcho.set(p.echo_chamber_strength);
    this.editEngagement.set(p.default_engagement_rate);
    this.editTonality.set(p.tonality_modifier || '');
    this.showEditDialog.set(true);
  }

  updatePlatform() {
    this.saving.set(true);
    this.platformService.update(this.editId(), {
      name: this.editName(),
      character: this.editCharacter(),
      reach_multiplier: this.editReach(),
      echo_chamber_strength: this.editEcho(),
      default_engagement_rate: this.editEngagement(),
      tonality_modifier: this.editTonality() || undefined,
    }).subscribe({
      next: () => { this.showEditDialog.set(false); this.saving.set(false); this.load(); },
      error: () => this.saving.set(false),
    });
  }

  deletePlatform(id: string, event: Event) {
    event.stopPropagation();
    this.platformService.delete(id).subscribe(() => this.load());
  }

  characterLabel(char: string): string {
    return this.characters.find(c => c.id === char)?.label || char;
  }
}
