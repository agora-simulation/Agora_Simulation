import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { NgxEchartsDirective, provideEchartsCore } from 'ngx-echarts';
import * as echarts from 'echarts';
import { PersonaService } from '../../../core/services/persona.service';
import { PostService } from '../../../core/services/post.service';
import { SimulationService } from '../../../core/services/simulation.service';
import { InfluenceEvent } from '../../../core/models/content.model';
import { Persona } from '../../../core/models/persona.model';
import { Simulation } from '../../../core/models/simulation.model';
import { CHART, FONT_MONO, FONT_SANS, tooltipStyle } from '../../../shared/chart-theme';

@Component({
  selector: 'app-influence',
  standalone: true,
  imports: [NgxEchartsDirective, FormsModule],
  providers: [provideEchartsCore({ echarts })],
  templateUrl: './influence.component.html',
})
export class InfluenceComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private personaService = inject(PersonaService);
  private postService = inject(PostService);
  private simService = inject(SimulationService);

  events = signal<InfluenceEvent[]>([]);
  personas = signal<Persona[]>([]);
  simulation = signal<Simulation | null>(null);
  sankeyChart = signal<any>({});
  topInfluencers = signal<{ id: string; name: string; count: number; isSceptic: boolean }[]>([]);
  // Fallback: Personas mit den meisten Posts (Proxy für Reichweite, wenn keine Events)
  topPosters = signal<{ name: string; count: number; isSceptic: boolean }[]>([]);
  loading = signal(true);

  // Tag-Filter
  selectedDay = signal<number | null>(null);
  visibleCount = signal(50);

  // Drill-Down
  expandedInfluencer = signal<string | null>(null); // persona_id

  // Influence-Type Chart
  typeBreakdownChart = signal<any>({});

  // Computed: verfügbare Tage
  availableDays = computed(() => {
    const days = new Set(this.events().map(e => e.ingame_day));
    return Array.from(days).sort((a, b) => a - b);
  });

  // Computed: gefilterte Events
  filteredEvents = computed(() => {
    let evts = this.events();
    const day = this.selectedDay();
    if (day !== null) {
      evts = evts.filter(e => e.ingame_day === day);
    }
    return evts.slice(0, this.visibleCount());
  });

  // Computed: hat mehr Events zum Laden?
  hasMoreEvents = computed(() => {
    let evts = this.events();
    const day = this.selectedDay();
    if (day !== null) {
      evts = evts.filter(e => e.ingame_day === day);
    }
    return evts.length > this.visibleCount();
  });

  private simId = '';

  ngOnInit() {
    this.simId = this.route.parent!.snapshot.params['id'];

    this.simService.getById(this.simId).subscribe(s => this.simulation.set(s));

    this.personaService.list(this.simId, { limit: 200 }).subscribe(res => {
      this.personas.set(res.items);

      this.simService.getInfluenceEvents(this.simId).subscribe({
        next: (influenceEvents) => {
          this.events.set(influenceEvents);
          this.buildSankeyChart(influenceEvents, res.items);
          this.buildTopInfluencers(influenceEvents, res.items);
          this.buildTypeBreakdown(influenceEvents);

          // Fallback: Top-Poster aus Posts berechnen
          this.postService.list(this.simId, { limit: 500 }).subscribe(postRes => {
            this.buildTopPosters(postRes.items, res.items);
            this.loading.set(false);
          });
        },
        error: () => this.loading.set(false),
      });
    });
  }

  private buildTopPosters(posts: any[], personas: Persona[]) {
    const countMap = new Map<string, number>();
    for (const post of posts) {
      countMap.set(post.author_id, (countMap.get(post.author_id) || 0) + 1);
    }
    const personaMap = new Map(personas.map(p => [p.id, p]));
    const sorted = Array.from(countMap.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([id, count]) => {
        const p = personaMap.get(id);
        return { name: p?.name || 'Unbekannt', count, isSceptic: p?.is_skeptic || false };
      });
    this.topPosters.set(sorted);
  }

  private buildSankeyChart(events: InfluenceEvent[], personas: Persona[]) {
    if (events.length === 0) return;

    const nameMap = new Map(personas.map(p => [p.id, p.name]));

    // Count influence relationships
    const linkMap = new Map<string, number>();
    for (const event of events) {
      const source = nameMap.get(event.source_persona_id) || 'Unbekannt';
      const target = nameMap.get(event.target_persona_id) || 'Unbekannt';
      const key = `${source}|||${target}`;
      linkMap.set(key, (linkMap.get(key) || 0) + 1);
    }

    // Build sankey data
    const nodeNames = new Set<string>();
    const links: { source: string; target: string; value: number }[] = [];

    for (const [key, count] of linkMap) {
      const [source, target] = key.split('|||');
      nodeNames.add(source);
      nodeNames.add(target);
      links.push({ source, target, value: count });
    }

    // Top 20 links for readability
    links.sort((a, b) => b.value - a.value);
    const topLinks = links.slice(0, 20);
    const usedNodes = new Set<string>();
    topLinks.forEach(l => { usedNodes.add(l.source); usedNodes.add(l.target); });

    this.sankeyChart.set({
      tooltip: { trigger: 'item', ...tooltipStyle },
      series: [{
        type: 'sankey',
        layout: 'none',
        emphasis: { focus: 'adjacency' },
        nodeAlign: 'justify',
        nodeWidth: 20,
        nodeGap: 14,
        data: Array.from(usedNodes).map(name => ({
          name,
          itemStyle: { color: CHART.feedbook, borderColor: 'rgba(90,159,214,0.4)', borderWidth: 1 },
        })),
        links: topLinks,
        lineStyle: { color: 'gradient', opacity: 0.35, curveness: 0.5 },
        label: {
          fontFamily: FONT_SANS,
          fontSize: 13,
          fontWeight: 500,
          color: CHART.ink,
        },
      }],
    });
  }

  private buildTopInfluencers(events: InfluenceEvent[], personas: Persona[]) {
    const countMap = new Map<string, number>();
    for (const event of events) {
      countMap.set(event.source_persona_id, (countMap.get(event.source_persona_id) || 0) + 1);
    }

    const personaMap = new Map(personas.map(p => [p.id, p]));

    const sorted = Array.from(countMap.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([id, count]) => {
        const p = personaMap.get(id);
        return { id, name: p?.name || 'Unbekannt', count, isSceptic: p?.is_skeptic || false };
      });

    this.topInfluencers.set(sorted);
  }

  setDayFilter(day: number | null) {
    this.selectedDay.set(day);
    this.visibleCount.set(50); // Reset pagination on filter change
  }

  loadMore() {
    this.visibleCount.update(v => v + 50);
  }

  toggleInfluencer(personaId: string) {
    this.expandedInfluencer.update(v => v === personaId ? null : personaId);
  }

  getInfluencerDetails(personaId: string): { targetName: string; type: string; description: string }[] {
    const personaMap = new Map(this.personas().map(p => [p.id, p.name]));
    return this.events()
      .filter(e => e.source_persona_id === personaId)
      .slice(0, 20) // max 20 Details
      .map(e => ({
        targetName: personaMap.get(e.target_persona_id) || 'Unbekannt',
        type: e.influence_type,
        description: e.description || '',
      }));
  }

  private buildTypeBreakdown(events: InfluenceEvent[]) {
    const typeMap = new Map<string, number>();
    for (const e of events) {
      typeMap.set(e.influence_type, (typeMap.get(e.influence_type) || 0) + 1);
    }

    const typeLabels: Record<string, string> = {
      'opinion_shift': 'Meinungsänderung',
      'positive_reaction': 'Positive Reaktion',
      'negative_reaction': 'Negative Reaktion',
      'engagement': 'Engagement',
    };

    const typeColors: Record<string, string> = {
      'opinion_shift': CHART.vermillion,
      'positive_reaction': CHART.moss,
      'negative_reaction': CHART.rust,
      'engagement': CHART.feedbook,
    };

    const data = Array.from(typeMap.entries()).map(([type, count]) => ({
      value: count,
      name: typeLabels[type] || type,
      itemStyle: { color: typeColors[type] || CHART.inkMute },
    }));

    this.typeBreakdownChart.set({
      tooltip: { trigger: 'item', ...tooltipStyle },
      series: [{
        type: 'pie',
        radius: ['50%', '75%'],
        avoidLabelOverlap: false,
        itemStyle: { borderColor: CHART.paper, borderWidth: 3, borderRadius: 4 },
        label: {
          show: true,
          formatter: '{b}\n{c} · {d}%',
          color: CHART.ink,
          fontFamily: FONT_SANS,
          fontSize: 13,
          fontWeight: 500,
          lineHeight: 18,
        },
        labelLine: { lineStyle: { color: CHART.paperEdge, width: 1 } },
        data,
      }],
    });
  }
}
