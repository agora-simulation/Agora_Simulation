import { Component, inject, signal, OnInit, computed, effect } from '@angular/core';
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
import { CHART, FONT_SANS, tooltipStyle, axisCommon, legendCommon, classifyMoodIndex, getMoodColor as getMoodColorShared } from '../../../shared/chart-theme';

interface MoodBucket { key: string; label: string; color: string; count: number; }

@Component({
  selector: 'app-overview',
  standalone: true,
  imports: [NgxEchartsDirective, TruncatePipe, RouterLink],
  providers: [provideEchartsCore({ echarts })],
  templateUrl: './overview.component.html',
})
export class OverviewComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private simService = inject(SimulationService);
  private personaService = inject(PersonaService);
  private postService = inject(PostService);

  simulation = signal<Simulation | null>(null);
  stats = signal<SimulationStats | null>(null);
  ticks = signal<TickSnapshot[]>([]);
  posts = signal<Post[]>([]);
  personas = signal<Persona[]>([]);
  activityChartOption = signal<any>({});
  moodChartOption = signal<any>({});

  private simId = '';

  // Derived
  recentPosts = computed(() => [...this.posts()].sort((a, b) => b.ingame_day - a.ingame_day).slice(0, 8));
  skepticCount = computed(() => this.personas().filter(p => p.is_skeptic).length);

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
  }

  private loadData() {
    this.simService.getById(this.simId).subscribe(s => this.simulation.set(s));
    this.simService.getStats(this.simId).subscribe(s => this.stats.set(s));
    this.simService.getTicks(this.simId).subscribe(t => { this.ticks.set(t); this.buildActivityChart(t); });
    this.postService.list(this.simId, { limit: 200 }).subscribe(r => this.posts.set(r.items));
    this.personaService.list(this.simId, { limit: 200 }).subscribe(r => this.personas.set(r.items));
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
}
