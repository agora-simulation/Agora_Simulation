import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { AnalysisService } from '../../../core/services/analysis.service';
import { ExportService } from '../../../core/services/export.service';
import { AnalysisReport } from '../../../core/models/analysis.model';

import { MarkdownPipe } from '../../../shared/pipes/markdown.pipe';

interface ReportSubSection {
  heading: string;
  icon: string;
  body: string;
}

const SUMMARY_SECTION_ICONS: Record<string, string> = {
  ausgangslage: 'pi-info-circle',
  kernerkenntnisse: 'pi-list-check',
  'risiken & chancen': 'pi-exclamation-triangle',
  'risiken und chancen': 'pi-exclamation-triangle',
  risiken: 'pi-exclamation-triangle',
  chancen: 'pi-star',
  'strategische empfehlungen': 'pi-compass',
  empfehlungen: 'pi-compass',
};

@Component({
  selector: 'app-report',
  standalone: true,
  imports: [MarkdownPipe],
  templateUrl: './report.component.html',
})
export class ReportComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private analysisService = inject(AnalysisService);
  protected exportService = inject(ExportService);

  report = signal<AnalysisReport | null>(null);
  loading = signal(true);
  regenerating = signal(false);
  noReport = signal(false);

  protected simId = '';

  /** Parse full_report into sub-sections by ### headers */
  summarySubSections = computed<ReportSubSection[]>(() => {
    const r = this.report();
    if (!r?.full_report) return [];
    return this._parseSections(r.full_report);
  });

  /** Intro text before the first ### header */
  summaryIntro = computed<string>(() => {
    const r = this.report();
    if (!r?.full_report) return '';
    const firstH3 = r.full_report.indexOf('\n###');
    if (firstH3 <= 0) return '';
    return r.full_report.substring(0, firstH3).trim();
  });

  ngOnInit() {
    this.simId = this.route.parent!.snapshot.params['id'];
    this.loadReport();
  }

  private loadReport() {
    this.loading.set(true);
    this.analysisService.getReport(this.simId).subscribe({
      next: (r) => {
        if (r === null) {
          this.noReport.set(true);
        } else {
          this.report.set(r);
        }
        this.loading.set(false);
      },
      error: () => {
        this.noReport.set(true);
        this.loading.set(false);
      },
    });
  }

  regenerate() {
    this.regenerating.set(true);
    this.analysisService.generateReport(this.simId).subscribe({
      next: (r) => {
        this.report.set(r);
        this.regenerating.set(false);
        this.noReport.set(false);
      },
      error: () => this.regenerating.set(false),
    });
  }

  getSectionContent(key: string): string | null {
    const r = this.report();
    if (!r) return null;
    return (r as Record<string, any>)[key] || null;
  }

  hasSection(key: string): boolean {
    const content = this.getSectionContent(key);
    if (!content) return false;
    const trimmed = content.trim();
    if (!trimmed) return false;
    const lower = trimmed.toLowerCase();
    if (lower.startsWith('placeholder') || lower === '—' || lower === '-' || lower === 'n/a') return false;
    return true;
  }

  scrollToSection(key: string): void {
    if (!this.hasSection(key)) return;
    const el = document.getElementById('section-' + key);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  scrollToSummarySection(index: number): void {
    const el = document.getElementById('summary-section-' + index);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  downloadReport(): void {
    const r = this.report();
    if (!r) return;

    let md = '# Analyse-Report\n\n';
    md += '## Zusammenfassung\n\n';
    md += (r.full_report || '') + '\n\n';

    for (const section of this.sections) {
      const content = this.getSectionContent(section.key);
      if (content && this.hasSection(section.key)) {
        md += `## ${section.label}\n\n`;
        md += content + '\n\n';
      }
    }

    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `report_${this.simId}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  readonly sections = [
    { key: 'sentiment_over_time', label: 'Sentiment-Verlauf', icon: 'pi-chart-line' },
    { key: 'key_turning_points', label: 'Wendepunkte', icon: 'pi-bolt' },
    { key: 'criticism_points', label: 'Kritikpunkte', icon: 'pi-exclamation-triangle' },
    { key: 'opportunities', label: 'Chancen', icon: 'pi-star' },
    { key: 'target_segment_analysis', label: 'Zielgruppen', icon: 'pi-users' },
    { key: 'unexpected_findings', label: 'Ueberraschungen', icon: 'pi-question-circle' },
    { key: 'influence_network', label: 'Influence-Netzwerk', icon: 'pi-share-alt' },
    { key: 'platform_dynamics', label: 'Plattform-Dynamik', icon: 'pi-desktop' },
    { key: 'network_evolution', label: 'Netzwerk-Evolution', icon: 'pi-sitemap' },
    { key: 'confidence_assessment', label: 'Konfidenz-Bewertung', icon: 'pi-verified' },
    { key: 'methodology_limitations', label: 'Methodische Grenzen', icon: 'pi-info-circle' },
  ];

  private _parseSections(markdown: string): ReportSubSection[] {
    const lines = markdown.split('\n');
    const sections: ReportSubSection[] = [];
    let currentHeading = '';
    let currentLines: string[] = [];

    for (const line of lines) {
      const match = line.match(/^###\s+(.+)$/);
      if (match) {
        if (currentHeading) {
          sections.push(this._makeSubSection(currentHeading, currentLines));
        }
        currentHeading = match[1].trim();
        currentLines = [];
      } else if (currentHeading) {
        currentLines.push(line);
      }
    }
    if (currentHeading) {
      sections.push(this._makeSubSection(currentHeading, currentLines));
    }
    return sections;
  }

  private _makeSubSection(heading: string, lines: string[]): ReportSubSection {
    const key = heading.toLowerCase().replace(/[*_]/g, '');
    const icon = SUMMARY_SECTION_ICONS[key] || 'pi-bookmark';
    return { heading, icon, body: lines.join('\n').trim() };
  }
}
