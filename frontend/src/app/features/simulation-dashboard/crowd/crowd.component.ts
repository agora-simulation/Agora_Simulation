import { Component, inject, signal, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { DecimalPipe } from '@angular/common';
import { CrowdService } from '../../../core/services/crowd.service';
import { CrowdState } from '../../../core/models/crowd.model';

@Component({
  selector: 'app-crowd',
  standalone: true,
  imports: [DecimalPipe],
  templateUrl: './crowd.component.html',
})
export class CrowdComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private crowdService = inject(CrowdService);

  simulationId = '';
  states = signal<CrowdState[]>([]);
  latest = signal<CrowdState | null>(null);
  loading = signal(true);

  ngOnInit() {
    this.simulationId = this.route.parent?.snapshot.paramMap.get('id') || '';
    this.loadData();
  }

  loadData() {
    this.loading.set(true);
    this.crowdService.getAll(this.simulationId).subscribe({
      next: states => {
        this.states.set(states);
        if (states.length > 0) this.latest.set(states[states.length - 1]);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  sentimentCssColor(sentiment: number): string {
    if (sentiment > 0.3) return 'var(--success)';
    if (sentiment < -0.3) return 'var(--danger)';
    return 'var(--warning)';
  }

  sentimentLabel(sentiment: number): string {
    if (sentiment > 0.5) return 'Sehr positiv';
    if (sentiment > 0.2) return 'Positiv';
    if (sentiment > -0.2) return 'Neutral';
    if (sentiment > -0.5) return 'Negativ';
    return 'Sehr negativ';
  }

  momentumIcon(momentum: number): string {
    if (momentum > 0.1) return 'pi pi-arrow-up';
    if (momentum < -0.1) return 'pi pi-arrow-down';
    return 'pi pi-minus';
  }
}
