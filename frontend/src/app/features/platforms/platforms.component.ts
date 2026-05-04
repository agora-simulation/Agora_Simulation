import { Component, inject, signal, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { PlatformService } from '../../core/services/platform.service';
import { SimPlatform } from '../../core/models/platform.model';

@Component({
  selector: 'app-platforms',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './platforms.component.html',
})
export class PlatformsComponent implements OnInit {
  private platformService = inject(PlatformService);

  platforms = signal<SimPlatform[]>([]);
  loading = signal(true);

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

  characterLabel(char: string): string {
    const map: Record<string, string> = { operativ: 'Operativ', institutionell: 'Institutionell', boulevard: 'Boulevard', fachlich: 'Fachlich', oeffentlich: 'Oeffentlich' };
    return map[char] || char;
  }
}
