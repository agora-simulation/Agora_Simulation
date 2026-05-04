import { Component, inject, signal, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { DatePipe } from '@angular/common';
import { ResearchSnapshotService } from '../../core/services/research-snapshot.service';
import { ResearchSnapshot } from '../../core/models/research-snapshot.model';

@Component({
  selector: 'app-research',
  standalone: true,
  imports: [RouterLink, FormsModule, DatePipe],
  templateUrl: './research.component.html',
})
export class ResearchComponent implements OnInit {
  private researchService = inject(ResearchSnapshotService);

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
    this.researchService.create({ name: this.newName() }).subscribe({
      next: () => { this.showCreateDialog.set(false); this.newName.set(''); this.load(); },
    });
  }

  approve(id: string) {
    this.researchService.approve(id).subscribe(() => this.load());
  }

  deleteSnapshot(id: string) {
    this.researchService.delete(id).subscribe(() => this.load());
  }

  statusColor(status: string): string {
    switch (status) {
      case 'approved': return 'text-green-400';
      case 'archived': return 'text-gray-500';
      default: return 'text-yellow-400';
    }
  }
}
