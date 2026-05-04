import { Component, inject, signal, OnInit } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { DatePipe } from '@angular/common';
import { ResearchSnapshotService } from '../../core/services/research-snapshot.service';
import { ResearchSnapshot } from '../../core/models/research-snapshot.model';
import { CardGlowDirective } from '../../shared/directives/card-glow.directive';

@Component({
  selector: 'app-research',
  standalone: true,
  imports: [RouterLink, FormsModule, DatePipe, CardGlowDirective],
  templateUrl: './research.component.html',
})
export class ResearchComponent implements OnInit {
  private researchService = inject(ResearchSnapshotService);
  private router = inject(Router);

  snapshots = signal<ResearchSnapshot[]>([]);
  loading = signal(true);
  showCreateDialog = signal(false);
  newName = signal('');

  ngOnInit() { this.load(); }

  load() {
    this.loading.set(true);
    this.researchService.list().subscribe({
      next: res => { this.snapshots.set(res.items); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  create() {
    if (!this.newName()) return;
    this.researchService.create({ name: this.newName() }).subscribe({
      next: snap => {
        this.showCreateDialog.set(false);
        this.newName.set('');
        this.router.navigate(['/research', snap.id]);
      },
    });
  }

  openSnapshot(id: string) {
    this.router.navigate(['/research', id]);
  }

  deleteSnapshot(id: string, event: Event) {
    event.stopPropagation();
    this.researchService.delete(id).subscribe(() => this.load());
  }

  statusBadge(status: string): string {
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

  resultPreview(snap: ResearchSnapshot): string {
    if (!snap.result) return '';
    return snap.result.length > 120 ? snap.result.substring(0, 120) + '...' : snap.result;
  }
}
