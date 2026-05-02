import { Component, inject, signal, OnInit, OnDestroy, computed, effect } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { NgxEchartsDirective, provideEchartsCore } from 'ngx-echarts';
import * as echarts from 'echarts';
import { SimulationService } from '../../../core/services/simulation.service';
import { PersonaService } from '../../../core/services/persona.service';
import { PostService } from '../../../core/services/post.service';
import { Simulation, SimulationStats, TickSnapshot } from '../../../core/models/simulation.model';
import { Post } from '../../../core/models/content.model';
import { Persona } from '../../../core/models/persona.model';
import { TruncatePipe } from '../../../shared/pipes/truncate.pipe';
import { CardGlowDirective } from '../../../shared/directives/card-glow.directive';
import { CHART, FONT_SANS, tooltipStyle, axisCommon, legendCommon, classifyMoodIndex, getMoodColor as getMoodColorShared } from '../../../shared/chart-theme';

interface MoodBucket { key: string; label: string; color: string; count: number; }

@Component({
  selector: 'app-overview',
  standalone: true,
  imports: [NgxEchartsDirective, TruncatePipe, RouterLink, CardGlowDirective],
  providers: [provideEchartsCore({ echarts })],
  templateUrl: './overview.component.html',
})
export class OverviewComponent implements OnInit, OnDestroy {
  private route = inject(ActivatedRoute);
  private simService = inject(SimulationService);
  private personaService = inject(PersonaService);
  private postService = inject(PostService);

  simulation = signal<Simulation | null>(null);
  stats = signal<SimulationStats | null>(null);
  ticks = signal<TickSnapshot[]>([]);
  posts = signal<Post[]>([]);
  personas = signal<Persona[]>([]);
  kpis = signal<any>(null);
  marketContext = signal<any>(null);
  approvingResearch = signal(false);
  private pollInterval: ReturnType<typeof setInterval> | null = null;
  activityChartOption = signal<any>({});
  moodChartOption = signal<any>({});
  engagementChartOption = signal<any>({});
  npsChartOption = signal<any>({});

  private simId = '';

  Math = Math;

  // Derived
  recentPosts = computed(() => [...this.posts()].sort((a, b) => b.ingame_day - a.ingame_day).slice(0, 8));
  skepticCount = computed(() => this.personas().filter(p => p.is_skeptic).length);

  private dimensionLabels: Record<string, string> = {
    product_quality: 'Produktqualität',
    price_fairness: 'Preis-Fairness',
    brand_trust: 'Markenvertrauen',
    innovation: 'Innovation',
    ethical_concerns: 'Ethik',
    social_proof: 'Social Proof',
    personal_relevance: 'Relevanz',
  };

  dimensionEntries = computed(() => {
    const dims = this.kpis()?.dimension_breakdown;
    if (!dims) return [];
    return Object.entries(dims).map(([key, val]: [string, any]) => ({
      key,
      label: this.dimensionLabels[key] || key,
      avg: val.avg,
      positive_pct: val.positive_pct,
      negative_pct: val.negative_pct,
    })).sort((a, b) => b.avg - a.avg);
  });

  moodBuckets = computed<MoodBucket[]>(() => {
    const buckets: MoodBucket[] = [
      { key: 'positiv',  label: 'Positiv',   color: CHART.moss,       count: 0 },
      { key: 'neugier',  label: 'Neugierig', color: CHART.feedbook,   count: 0 },
      { key: 'neutral',  label: 'Neutral',   color: CHART.inkMute,    count: 0 },
      { key: 'skepti',   label: 'Skeptisch', color: CHART.threadit,   count: 0 },
      { key: 'negativ',  label: 'Negativ',   color: CHART.vermillion, count: 0 },
    ];
    for (const p of this.personas()) {
      const m = (p.current_state?.mood || '').toLowerCase();
      if (!m) { buckets[2].count++; continue; }
      const idx = classifyMoodIndex(m);
      buckets[idx].count++;
    }
    return buckets;
  });

  constructor() {
    effect(() => {
      const buckets = this.moodBuckets();
      this.buildMoodChart(buckets);
    });
  }

  ngOnInit() {
    this.simId = this.route.parent!.snapshot.params['id'];
    this.loadData();
    // Auto-Refresh alle 5 Sekunden wenn Simulation aktiv
    this.pollInterval = setInterval(() => {
      const sim = this.simulation();
      if (sim && ['running', 'researching', 'pending'].includes(sim.status)) {
        this.loadData();
      }
    }, 5000);
  }

  ngOnDestroy() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
  }

  getStatusPhaseLabel(): string {
    const sim = this.simulation();
    if (!sim) return '';
    switch (sim.status) {
      case 'pending': return 'Simulation wird vorbereitet...';
      case 'researching': return 'Web-Recherche läuft — aktuelle Marktdaten werden analysiert';
      case 'research_complete': return 'Recherche abgeschlossen — bitte prüfen und bestätigen';
      case 'running': {
        const tick = sim.current_tick;
        const total = sim.total_ticks;
        if (tick === 0) return 'Personas werden generiert...';
        return `Tag ${tick} von ${total} wird simuliert — Personas interagieren`;
      }
      case 'completed': return '';
      case 'failed': return 'Simulation fehlgeschlagen';
      default: return '';
    }
  }

  isSimulationActive(): boolean {
    const sim = this.simulation();
    return !!sim && ['running', 'researching', 'pending'].includes(sim.status);
  }

  private loadData() {
    this.simService.getById(this.simId).subscribe(s => {
      this.simulation.set(s);
      // MarketContext laden wenn Deep Mode
      if (s.research_mode === 'deep') {
        this.simService.getMarketContext(this.simId).subscribe({
          next: ctx => this.marketContext.set(ctx),
          error: () => {},
        });
      }
    });
    this.simService.getStats(this.simId).subscribe(s => this.stats.set(s));
    this.simService.getTicks(this.simId).subscribe(t => { this.ticks.set(t); this.buildActivityChart(t); });
    this.postService.list(this.simId, { limit: 200 }).subscribe(r => this.posts.set(r.items));
    this.personaService.list(this.simId, { limit: 200 }).subscribe(r => this.personas.set(r.items));
    this.simService.getKpis(this.simId).subscribe({
      next: k => { this.kpis.set(k); this.buildEngagementChart(k); this.buildNpsChart(k); },
      error: () => {},
    });
  }

  approveResearch() {
    this.approvingResearch.set(true);
    this.simService.approveResearch(this.simId).subscribe({
      next: () => {
        this.approvingResearch.set(false);
        this.loadData();
      },
      error: () => this.approvingResearch.set(false),
    });
  }

  private buildActivityChart(ticks: TickSnapshot[]) {
    this.activityChartOption.set({
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis', ...tooltipStyle },
      legend: legendCommon(['Beiträge', 'Kommentare', 'Reaktionen']),
      grid: { top: 16, right: 16, bottom: 44, left: 44 },
      xAxis: {
        type: 'category',
        data: ticks.map(t => `${t.ingame_day}`),
        ...axisCommon({
          axisLabel: { color: CHART.inkMute, fontFamily: FONT_SANS, fontSize: 11, formatter: (v: string) => `T${v}` },
          splitLine: { show: false },
        }),
      },
      yAxis: {
        type: 'value',
        ...axisCommon({
          axisLabel: { color: CHART.inkMute, fontFamily: FONT_SANS, fontSize: 11 },
        }),
      },
      series: [
        { name: 'Beiträge',   type: 'bar', stack: 'a', data: ticks.map(t => t.snapshot.new_posts),     itemStyle: { color: CHART.ink, borderRadius: [2, 2, 0, 0] }, barWidth: '55%' },
        { name: 'Kommentare', type: 'bar', stack: 'a', data: ticks.map(t => t.snapshot.new_comments),  itemStyle: { color: CHART.vermillion } },
        { name: 'Reaktionen', type: 'bar', stack: 'a', data: ticks.map(t => t.snapshot.new_reactions), itemStyle: { color: CHART.threadit } },
      ],
    });
  }

  private buildMoodChart(buckets: MoodBucket[]) {
    this.moodChartOption.set({
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, ...tooltipStyle },
      grid: { top: 8, right: 16, bottom: 28, left: 90 },
      xAxis: {
        type: 'value',
        ...axisCommon({
          axisLabel: { color: CHART.inkMute, fontFamily: FONT_SANS, fontSize: 11 },
          splitLine: { lineStyle: { color: CHART.paperEdge, type: 'dashed' } },
        }),
      },
      yAxis: {
        type: 'category',
        data: buckets.map(b => b.label),
        inverse: true,
        ...axisCommon({
          axisLabel: { color: CHART.ink, fontFamily: FONT_SANS, fontSize: 12, fontWeight: 500 },
          splitLine: { show: false },
        }),
      },
      series: [
        {
          type: 'bar',
          data: buckets.map(b => ({ value: b.count, itemStyle: { color: b.color, borderRadius: [0, 4, 4, 0] } })),
          barWidth: 22,
          label: { show: true, position: 'right', color: CHART.ink, fontFamily: FONT_SANS, fontSize: 11, fontWeight: 600 },
        },
      ],
    });
  }

  getMoodColor(mood: string | undefined): string {
    return getMoodColorShared(mood);
  }

  getNpsColor(score: number): string {
    if (score >= 50) return CHART.moss;
    if (score >= 0) return CHART.threadit;
    return CHART.vermillion;
  }

  getSentimentLabel(score: number): string {
    if (score > 0.3) return 'Sehr positiv';
    if (score > 0.1) return 'Positiv';
    if (score > -0.1) return 'Neutral';
    if (score > -0.3) return 'Negativ';
    return 'Sehr negativ';
  }

  private buildEngagementChart(kpis: any) {
    if (!kpis?.engagement_rate?.length) return;
    const data = kpis.engagement_rate;
    this.engagementChartOption.set({
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis', ...tooltipStyle },
      grid: { top: 16, right: 16, bottom: 44, left: 44 },
      xAxis: {
        type: 'category',
        data: data.map((d: any) => `${d.day}`),
        ...axisCommon({
          axisLabel: { color: CHART.inkMute, fontFamily: FONT_SANS, fontSize: 11, formatter: (v: string) => `T${v}` },
          splitLine: { show: false },
        }),
      },
      yAxis: {
        type: 'value',
        ...axisCommon({
          axisLabel: { color: CHART.inkMute, fontFamily: FONT_SANS, fontSize: 11 },
        }),
      },
      series: [
        {
          name: 'Engagement Rate',
          type: 'line',
          data: data.map((d: any) => d.rate),
          smooth: true,
          symbol: 'circle',
          symbolSize: 6,
          lineStyle: { color: CHART.feedbook, width: 2 },
          itemStyle: { color: CHART.feedbook },
          areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [
            { offset: 0, color: 'rgba(30, 58, 138, 0.15)' },
            { offset: 1, color: 'rgba(30, 58, 138, 0.02)' },
          ]}},
        },
      ],
    });
  }

  private buildNpsChart(kpis: any) {
    if (!kpis?.nps) return;
    const nps = kpis.nps;
    this.npsChartOption.set({
      backgroundColor: 'transparent',
      tooltip: { trigger: 'item', ...tooltipStyle },
      series: [{
        type: 'pie',
        radius: ['55%', '75%'],
        avoidLabelOverlap: false,
        label: { show: false },
        data: [
          { value: nps.promoters, name: 'Promoter', itemStyle: { color: CHART.moss } },
          { value: nps.passives, name: 'Passive', itemStyle: { color: CHART.inkMute } },
          { value: nps.detractors, name: 'Detractor', itemStyle: { color: CHART.vermillion } },
        ],
      }],
    });
  }
}
