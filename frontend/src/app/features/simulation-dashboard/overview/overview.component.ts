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
import { ThemeService } from '../../../core/services/theme.service';
import {
  getChartColors, getTooltipStyle, getAxisCommon, getLegendCommon,
  getMoodColors, classifyMoodIndex, getMoodColor as getMoodColorShared,
  FONT_SANS,
} from '../../../shared/chart-theme';

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
  private theme = inject(ThemeService);

  simulation = signal<Simulation | null>(null);
  stats = signal<SimulationStats | null>(null);
  ticks = signal<TickSnapshot[]>([]);
  posts = signal<Post[]>([]);
  personas = signal<Persona[]>([]);
  kpis = signal<any>(null);
  marketContext = signal<any>(null);
  approvingResearch = signal(false);
  resuming = signal(false);
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
    const isDark = this.theme.isDarkMode();
    const colors = getMoodColors(isDark);
    const buckets: MoodBucket[] = [
      { key: 'positiv',  label: 'Positiv',   color: colors[0], count: 0 },
      { key: 'neugier',  label: 'Neugierig', color: colors[1], count: 0 },
      { key: 'neutral',  label: 'Neutral',   color: colors[2], count: 0 },
      { key: 'skepti',   label: 'Skeptisch', color: colors[3], count: 0 },
      { key: 'negativ',  label: 'Negativ',   color: colors[4], count: 0 },
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
    // Rebuild all charts when theme or data changes
    effect(() => {
      const buckets = this.moodBuckets();
      this.buildMoodChart(buckets);
    });
    effect(() => {
      const _isDark = this.theme.isDarkMode();
      const t = this.ticks();
      if (t.length) this.buildActivityChart(t);
      const k = this.kpis();
      if (k) { this.buildEngagementChart(k); this.buildNpsChart(k); }
    });
  }

  ngOnInit() {
    this.simId = this.route.parent!.snapshot.params['id'];
    this.loadData();
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
        const est = this.estimatedRemaining();
        const suffix = est ? ` — ca. ${est} verbleibend` : '';
        return `Tag ${tick} von ${total} wird simuliert${suffix}`;
      }
      case 'completed': return '';
      case 'failed': return 'Simulation fehlgeschlagen';
      default: return '';
    }
  }

  estimatedRemaining(): string {
    const t = this.ticks();
    const sim = this.simulation();
    if (!sim || t.length < 2) return '';
    const timestamps = t.map(tick => new Date(tick.created_at).getTime()).sort((a, b) => a - b);
    const diffs: number[] = [];
    for (let i = 1; i < timestamps.length; i++) {
      diffs.push(timestamps[i] - timestamps[i - 1]);
    }
    if (diffs.length === 0) return '';
    const avgMs = diffs.reduce((a, b) => a + b, 0) / diffs.length;
    const remainingTicks = sim.total_ticks - sim.current_tick;
    const remainingMs = avgMs * remainingTicks;
    const remainingMin = Math.ceil(remainingMs / 60000);
    if (remainingMin < 1) return '< 1 Min';
    if (remainingMin < 60) return `${remainingMin} Min`;
    const h = Math.floor(remainingMin / 60);
    const m = remainingMin % 60;
    return m === 0 ? `${h} Std` : `${h} Std ${m} Min`;
  }

  isSimulationActive(): boolean {
    const sim = this.simulation();
    return !!sim && ['running', 'researching', 'pending'].includes(sim.status);
  }

  private loadData() {
    this.simService.getById(this.simId).subscribe(s => {
      this.simulation.set(s);
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

  resumeSimulation() {
    this.resuming.set(true);
    this.simService.resume(this.simId).subscribe({
      next: () => {
        this.resuming.set(false);
        window.location.reload();
      },
      error: () => this.resuming.set(false),
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
    const isDark = this.theme.isDarkMode();
    const C = getChartColors(isDark);
    this.activityChartOption.set({
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis', ...getTooltipStyle(isDark) },
      legend: getLegendCommon(isDark, ['Beiträge', 'Kommentare', 'Reaktionen']),
      grid: { top: 16, right: 16, bottom: 44, left: 44 },
      xAxis: {
        type: 'category',
        data: ticks.map(t => `${t.ingame_day}`),
        ...getAxisCommon(isDark, {
          axisLabel: { color: C.inkMute, fontFamily: FONT_SANS, fontSize: 11, formatter: (v: string) => `T${v}` },
          splitLine: { show: false },
        }),
      },
      yAxis: {
        type: 'value',
        ...getAxisCommon(isDark),
      },
      series: [
        { name: 'Beiträge',   type: 'bar', stack: 'a', data: ticks.map(t => t.snapshot.new_posts),     itemStyle: { color: C.ink, borderRadius: [2, 2, 0, 0] }, barWidth: '55%' },
        { name: 'Kommentare', type: 'bar', stack: 'a', data: ticks.map(t => t.snapshot.new_comments),  itemStyle: { color: C.vermillion } },
        { name: 'Reaktionen', type: 'bar', stack: 'a', data: ticks.map(t => t.snapshot.new_reactions), itemStyle: { color: C.threadit } },
      ],
    });
  }

  private buildMoodChart(buckets: MoodBucket[]) {
    const isDark = this.theme.isDarkMode();
    const C = getChartColors(isDark);
    this.moodChartOption.set({
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, ...getTooltipStyle(isDark) },
      grid: { top: 8, right: 16, bottom: 28, left: 90 },
      xAxis: {
        type: 'value',
        ...getAxisCommon(isDark, {
          splitLine: { lineStyle: { color: C.paperEdge, type: 'dashed' } },
        }),
      },
      yAxis: {
        type: 'category',
        data: buckets.map(b => b.label),
        inverse: true,
        ...getAxisCommon(isDark, {
          axisLabel: { color: C.ink, fontFamily: FONT_SANS, fontSize: 12, fontWeight: 500 },
          splitLine: { show: false },
        }),
      },
      series: [
        {
          type: 'bar',
          data: buckets.map(b => ({ value: b.count, itemStyle: { color: b.color, borderRadius: [0, 4, 4, 0] } })),
          barWidth: 22,
          label: { show: true, position: 'right', color: C.ink, fontFamily: FONT_SANS, fontSize: 11, fontWeight: 600 },
        },
      ],
    });
  }

  getMoodColor(mood: string | undefined): string {
    return getMoodColorShared(mood);
  }

  getNpsColor(score: number): string {
    const C = getChartColors(this.theme.isDarkMode());
    if (score >= 50) return C.moss;
    if (score >= 0) return C.threadit;
    return C.vermillion;
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
    const isDark = this.theme.isDarkMode();
    const C = getChartColors(isDark);
    const data = kpis.engagement_rate;
    this.engagementChartOption.set({
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis', ...getTooltipStyle(isDark) },
      grid: { top: 16, right: 16, bottom: 44, left: 44 },
      xAxis: {
        type: 'category',
        data: data.map((d: any) => `${d.day}`),
        ...getAxisCommon(isDark, {
          axisLabel: { color: C.inkMute, fontFamily: FONT_SANS, fontSize: 11, formatter: (v: string) => `T${v}` },
          splitLine: { show: false },
        }),
      },
      yAxis: {
        type: 'value',
        ...getAxisCommon(isDark),
      },
      series: [
        {
          name: 'Engagement Rate',
          type: 'line',
          data: data.map((d: any) => d.rate),
          smooth: true,
          symbol: 'circle',
          symbolSize: 6,
          lineStyle: { color: C.feedbook, width: 2 },
          itemStyle: { color: C.feedbook },
          areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [
            { offset: 0, color: isDark ? 'rgba(90, 159, 214, 0.15)' : 'rgba(42, 122, 184, 0.12)' },
            { offset: 1, color: isDark ? 'rgba(90, 159, 214, 0.02)' : 'rgba(42, 122, 184, 0.02)' },
          ]}},
        },
      ],
    });
  }

  private buildNpsChart(kpis: any) {
    if (!kpis?.nps) return;
    const isDark = this.theme.isDarkMode();
    const C = getChartColors(isDark);
    const nps = kpis.nps;
    this.npsChartOption.set({
      backgroundColor: 'transparent',
      tooltip: { trigger: 'item', ...getTooltipStyle(isDark) },
      series: [{
        type: 'pie',
        radius: ['55%', '75%'],
        avoidLabelOverlap: false,
        label: { show: false },
        data: [
          { value: nps.promoters, name: 'Promoter', itemStyle: { color: C.moss } },
          { value: nps.passives, name: 'Passive', itemStyle: { color: C.inkMute } },
          { value: nps.detractors, name: 'Detractor', itemStyle: { color: C.vermillion } },
        ],
      }],
    });
  }
}
