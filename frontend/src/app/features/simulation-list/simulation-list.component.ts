import { Component, inject, signal, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { SimulationService } from '../../core/services/simulation.service';
import { Simulation, SimulationStatus } from '../../core/models/simulation.model';
import { RelativeTimePipe } from '../../shared/pipes/relative-time.pipe';
import { CardGlowDirective } from '../../shared/directives/card-glow.directive';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-simulation-list',
  standalone: true,
  imports: [RouterLink, RelativeTimePipe, FormsModule, CardGlowDirective],
  templateUrl: './simulation-list.component.html',
})
export class SimulationListComponent implements OnInit {
  private simService = inject(SimulationService);

  simulations = signal<Simulation[]>([]);
  loading = signal(true);
  searchTerm = signal('');
  statusFilter = signal<SimulationStatus | ''>('');

  ngOnInit() { this.loadSimulations(); }

  loadSimulations() {
    this.loading.set(true);
    const params: Record<string, string | number> = { limit: 50, offset: 0 };
    if (this.statusFilter()) params['status'] = this.statusFilter();
    if (this.searchTerm()) params['name'] = this.searchTerm();
    this.simService.list(params as any).subscribe({
      next: (res) => { this.simulations.set(res.items); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  deleteSimulation(id: string, event: Event) {
    event.preventDefault();
    event.stopPropagation();
    if (confirm('Simulation wirklich löschen?')) {
      this.simService.delete(id).subscribe(() => this.loadSimulations());
    }
  }

  getStatusLabel(status: string): string {
    switch (status) {
      case 'pending': return 'Ausstehend';
      case 'running': return 'Läuft';
      case 'completed': return 'Abgeschlossen';
      case 'failed': return 'Fehlgeschlagen';
      default: return status;
    }
  }

  getProgress(sim: Simulation): number {
    if (!sim.total_ticks) return 0;
    return Math.round((sim.current_tick / sim.total_ticks) * 100);
  }
}
