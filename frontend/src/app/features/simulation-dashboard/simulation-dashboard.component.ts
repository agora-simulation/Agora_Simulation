import { Component, inject, signal, OnInit, OnDestroy } from '@angular/core';
import { ActivatedRoute, Router, RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { Subscription } from 'rxjs';
import { SimulationService } from '../../core/services/simulation.service';
import { PersonaService } from '../../core/services/persona.service';
import { PostService } from '../../core/services/post.service';
import { SseService } from '../../core/services/sse.service';
import { Simulation } from '../../core/models/simulation.model';
import { Persona } from '../../core/models/persona.model';
import { Post } from '../../core/models/content.model';
import { ActivityConsoleComponent } from '../../shared/components/activity-console.component';

interface Tab { route: string; label: string; icon: string; }

@Component({
  selector: 'app-simulation-dashboard',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, ActivityConsoleComponent],
  templateUrl: './simulation-dashboard.component.html',
})
export class SimulationDashboardComponent implements OnInit, OnDestroy {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private simService = inject(SimulationService);
  private personaService = inject(PersonaService);
  private postService = inject(PostService);
  private sseService = inject(SseService);
  private sseSub?: Subscription;

  simulation = signal<Simulation | null>(null);
  personas = signal<Persona[]>([]);
  posts = signal<Post[]>([]);
  loading = signal(true);

  // Header-Zustand: kollabiert/expandiert (LocalStorage-persistiert)
  headerCollapsed = signal<boolean>(localStorage.getItem('agora_header_collapsed') === '1');

  simulationId = '';

  toggleHeader() {
    const next = !this.headerCollapsed();
    this.headerCollapsed.set(next);
    localStorage.setItem('agora_header_collapsed', next ? '1' : '0');
  }

  readonly tabs: Tab[] = [
    { route: 'overview',  label: 'Übersicht',  icon: 'pi-chart-bar' },
    { route: 'personas',  label: 'Personas',   icon: 'pi-users' },
    { route: 'network',   label: 'Netzwerk',   icon: 'pi-share-alt' },
    { route: 'sentiment', label: 'Sentiment',  icon: 'pi-chart-line' },
    { route: 'influence', label: 'Einfluss',   icon: 'pi-arrows-alt' },
    { route: 'report',    label: 'Report',     icon: 'pi-file' },
    { route: 'tools',     label: 'Werkzeuge',  icon: 'pi-wrench' },
  ];

  private static readonly UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

  ngOnInit() {
    this.simulationId = this.route.snapshot.params['id'];
    if (!SimulationDashboardComponent.UUID_RE.test(this.simulationId)) {
      this.router.navigate(['/simulations']);
      return;
    }
    this.loadData();
  }

  ngOnDestroy() {
    this.sseSub?.unsubscribe();
  }

  private loadData() {
    this.simService.getById(this.simulationId).subscribe(sim => {
      this.simulation.set(sim);
      this.loading.set(false);

      if (sim.status === 'running') {
        this.connectSSE();
      }
    });

    this.personaService.list(this.simulationId, { limit: 200 }).subscribe(res => {
      this.personas.set(res.items);
    });

    this.postService.list(this.simulationId, { limit: 500 }).subscribe(res => {
      this.posts.set(res.items);
    });
  }

  private connectSSE() {
    this.sseSub = this.sseService.connect(this.simulationId).subscribe({
      next: (event) => {
        this.simulation.update(sim => sim ? {
          ...sim,
          current_tick: event.current_tick,
          status: event.status,
        } : sim);

        if (event.status === 'completed') {
          this.loadData();
        }
      },
    });
  }

  tabCounter(route: string): number | null {
    if (route === 'personas') return this.personas().length || null;
    return null;
  }

  get progress(): number {
    const sim = this.simulation();
    if (!sim || !sim.total_ticks) return 0;
    return Math.round((sim.current_tick / sim.total_ticks) * 100);
  }
}
