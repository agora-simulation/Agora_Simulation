import { Component, inject, signal, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { KeyValuePipe } from '@angular/common';
import { TemplateService } from '../../core/services/template.service';
import { Template, TemplateCategory } from '../../core/models/template.model';

@Component({
  selector: 'app-templates',
  standalone: true,
  imports: [FormsModule, KeyValuePipe],
  templateUrl: './templates.component.html',
})
export class TemplatesComponent implements OnInit {
  private templateService = inject(TemplateService);

  templates = signal<Template[]>([]);
  loading = signal(true);
  activeCategory = signal<TemplateCategory>('distribution');

  categories: { id: TemplateCategory; label: string; icon: string }[] = [
    { id: 'distribution', label: 'Verteilung', icon: 'pi-chart-pie' },
    { id: 'tonality', label: 'Tonalitaet', icon: 'pi-comment' },
    { id: 'research', label: 'Recherche', icon: 'pi-search' },
    { id: 'trigger_library', label: 'Trigger-Library', icon: 'pi-bolt' },
  ];

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

  deleteTemplate(id: string) {
    this.templateService.delete(id).subscribe(() => this.load());
  }
}
