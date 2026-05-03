import { Component, inject, signal, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { NgxEchartsDirective, provideEchartsCore } from 'ngx-echarts';
import { PostService } from '../../../core/services/post.service';
import { SimulationService } from '../../../core/services/simulation.service';
import { Post } from '../../../core/models/content.model';
import { TickSnapshot } from '../../../core/models/simulation.model';
import { EChartsOption } from 'echarts';
import * as echarts from 'echarts';
import { CHART, FONT_MONO, FONT_SANS, tooltipStyle, axisCommon, legendCommon } from '../../../shared/chart-theme';

@Component({
  selector: 'app-sentiment',
  standalone: true,
  imports: [NgxEchartsDirective],
  providers: [provideEchartsCore({ echarts })],
  templateUrl: './sentiment.component.html',
})
export class SentimentComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private postService = inject(PostService);
  private simService = inject(SimulationService);

  platformChart = signal<EChartsOption>({});
  activityChart = signal<EChartsOption>({});
  polarizationChart = signal<EChartsOption>({});
  reactionsChart = signal<EChartsOption>({});
  engagementChart = signal<EChartsOption>({});
  opinionRadarChart = signal<EChartsOption>({});
  clusterChart = signal<EChartsOption>({});
  polarizationIndex = signal(0);
  hasPolarization = signal(false);
  hasReactions = signal(false);
  hasEngagement = signal(false);
  hasOpinionDims = signal(false);
  hasClusters = signal(false);
  totalPosts = signal(0);
  loading = signal(true);

  private simId = '';

  ngOnInit() {
    this.simId = this.route.parent!.snapshot.params['id'];
    this.loadData();
  }

  private loadData() {
    this.postService.list(this.simId, { limit: 500 }).subscribe(res => {
      this.buildPlatformChart(res.items);
      this.loading.set(false);
    });
    this.simService.getTicks(this.simId).subscribe(ticks => {
      this.buildActivityChart(ticks);
    });
    this.simService.getSentimentStats(this.simId).subscribe(stats => {
      if (stats.reactions_by_day?.length > 0) {
        this.buildReactionsChart(stats.reactions_by_day);
        this.hasReactions.set(true);
      }
      if (stats.engagement_by_day?.length > 0) {
        this.buildEngagementChart(stats.engagement_by_day);
        this.hasEngagement.set(true);
      }
      if (stats.opinion_dimensions) {
        this.buildOpinionRadarChart(stats.opinion_dimensions);
        this.hasOpinionDims.set(true);
      }
    });
  }

  private buildPlatformChart(posts: Post[]) {
    const feedbook = posts.filter(p => p.platform === 'feedbook').length;
    const threadit = posts.filter(p => p.platform === 'threadit').length;
    this.totalPosts.set(feedbook + threadit);

    this.platformChart.set({
      tooltip: { trigger: 'item', ...tooltipStyle },
      legend: legendCommon(['FeedBook', 'Threadit']),
      series: [{
        type: 'pie',
        radius: ['58%', '80%'],
        avoidLabelOverlap: false,
        itemStyle: { borderColor: CHART.paper, borderWidth: 3, borderRadius: 4 },
        label: {
          show: true,
          formatter: '{b}\n{c} · {d}%',
          color: CHART.ink,
          fontFamily: FONT_SANS,
          fontSize: 12,
          fontWeight: 500,
          lineHeight: 16,
        },
        labelLine: { lineStyle: { color: CHART.paperEdge, width: 1 } },
        data: [
          { value: feedbook, name: 'FeedBook', itemStyle: { color: CHART.feedbook } },
          { value: threadit, name: 'Threadit', itemStyle: { color: CHART.threadit } },
        ],
      }],
    });
  }

  private buildActivityChart(ticks: TickSnapshot[]) {
    this.activityChart.set({
      tooltip: { trigger: 'axis', ...tooltipStyle },
      grid: { top: 16, right: 16, bottom: 32, left: 44 },
      xAxis: {
        type: 'category',
        data: ticks.map(t => `T${t.ingame_day}`),
        ...axisCommon({ splitLine: { show: false } }),
      },
      yAxis: { type: 'value', ...axisCommon() },
      series: [{
        type: 'line',
        data: ticks.map(t => t.snapshot.personas_active),
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { color: CHART.vermillion, width: 2 },
        itemStyle: { color: CHART.vermillion, borderColor: CHART.paperDeep, borderWidth: 2 },
        areaStyle: { color: CHART.vermillion, opacity: 0.12 },
        name: 'Aktive Personas',
      }],
    });

    // Modul 5: Polarisierungs-Index aus letztem Tick
    const lastTick = ticks.filter(t => t.snapshot.polarization_index !== undefined).at(-1);
    if (lastTick?.snapshot?.polarization_index !== undefined) {
      const idx = lastTick.snapshot.polarization_index;
      this.polarizationIndex.set(idx);
      this.hasPolarization.set(true);
      this.buildPolarizationChart(idx);
    }

    // Echo-Chamber Cluster über Zeit
    const clusterTicks = ticks.filter(t => (t.snapshot.echo_chamber_clusters?.length ?? 0) >= 2);
    if (clusterTicks.length > 0) {
      this.buildClusterChart(clusterTicks);
      this.hasClusters.set(true);
    }
  }

  private buildPolarizationChart(index: number) {
    // Gauge 0-1 (Standardabweichung der Meinungen)
    const pct = Math.round(Math.min(index / 0.7 * 100, 100)); // 0.7 = max expected stdev
    const color = pct < 30 ? CHART.moss : pct < 60 ? CHART.threadit : CHART.rust;

    this.polarizationChart.set({
      tooltip: { formatter: `Polarisierung: ${(index).toFixed(3)}` },
      series: [({
        type: 'gauge',
        startAngle: 200,
        endAngle: -20,
        min: 0,
        max: 100,
        radius: '90%',
        pointer: { show: false },
        progress: { show: true, overlap: false, roundCap: true, clip: false,
          itemStyle: { color } },
        axisLine: { lineStyle: { width: 16, color: [[1, 'rgba(230,183,113,0.08)']] } },
        splitLine: { show: false },
        axisTick: { show: false },
        axisLabel: { show: false },
        detail: {
          valueAnimation: true,
          formatter: `{value}%\nPolarisierung`,
          color: CHART.ink,
          fontSize: 14,
          fontWeight: '700',
          lineHeight: 18,
        },
        data: [{ value: pct }],
      }) as any],
    });
  }

  private buildReactionsChart(data: any[]) {
    // Aggregiere pro Tag (über alle Plattformen)
    const dayMap = new Map<number, {likes: number, dislikes: number, shares: number}>();
    for (const r of data) {
      const existing = dayMap.get(r.ingame_day) || {likes: 0, dislikes: 0, shares: 0};
      existing.likes += r.likes;
      existing.dislikes += r.dislikes;
      existing.shares += r.shares;
      dayMap.set(r.ingame_day, existing);
    }
    const days = Array.from(dayMap.keys()).sort((a, b) => a - b);
    const vals = days.map(d => dayMap.get(d)!);

    this.reactionsChart.set({
      tooltip: { trigger: 'axis', ...tooltipStyle },
      legend: legendCommon(['Likes', 'Dislikes', 'Shares']),
      grid: { top: 16, right: 16, bottom: 44, left: 44 },
      xAxis: {
        type: 'category',
        data: days.map(d => `T${d}`),
        ...axisCommon({ splitLine: { show: false } }),
      },
      yAxis: { type: 'value', ...axisCommon() },
      series: [
        { name: 'Likes', type: 'bar', stack: 'r', data: vals.map(v => v.likes), itemStyle: { color: CHART.moss, borderRadius: [2, 2, 0, 0] }, barWidth: '50%' },
        { name: 'Dislikes', type: 'bar', stack: 'r', data: vals.map(v => v.dislikes), itemStyle: { color: CHART.rust } },
        { name: 'Shares', type: 'bar', stack: 'r', data: vals.map(v => v.shares), itemStyle: { color: CHART.feedbook } },
      ],
    });
  }

  private buildEngagementChart(data: any[]) {
    this.engagementChart.set({
      tooltip: { trigger: 'axis', ...tooltipStyle },
      grid: { top: 16, right: 16, bottom: 32, left: 44 },
      xAxis: {
        type: 'category',
        data: data.map(d => `T${d.ingame_day}`),
        ...axisCommon({ splitLine: { show: false } }),
      },
      yAxis: { type: 'value', ...axisCommon() },
      series: [{
        type: 'line',
        data: data.map(d => d.engagement_rate),
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { color: CHART.feedbook, width: 2 },
        itemStyle: { color: CHART.feedbook, borderColor: CHART.paperDeep, borderWidth: 2 },
        areaStyle: { color: CHART.feedbook, opacity: 0.1 },
        name: 'Kommentare / Beitr\u00e4ge',
      }],
    });
  }

  private buildOpinionRadarChart(dims: any) {
    const labels: Record<string, string> = {
      product_quality: 'Qualit\u00e4t',
      price_fairness: 'Preis',
      brand_trust: 'Vertrauen',
      innovation: 'Innovation',
      ethical_concerns: 'Ethik',
      social_proof: 'Sozial',
      personal_relevance: 'Relevanz',
    };
    const keys = Object.keys(labels);
    const indicators = keys.map(k => ({ name: labels[k], max: 1 }));

    const normalize = (v: number) => Math.round(((v + 1) / 2) * 100) / 100;

    const series: any[] = [];
    if (dims.non_skeptic) {
      series.push({
        value: keys.map(k => normalize(dims.non_skeptic[k] || 0)),
        name: 'Bef\u00fcrworter',
        itemStyle: { color: CHART.moss },
        lineStyle: { color: CHART.moss, width: 2 },
        areaStyle: { color: CHART.moss, opacity: 0.1 },
      });
    }
    if (dims.skeptic) {
      series.push({
        value: keys.map(k => normalize(dims.skeptic[k] || 0)),
        name: 'Skeptiker',
        itemStyle: { color: CHART.vermillion },
        lineStyle: { color: CHART.vermillion, width: 2 },
        areaStyle: { color: CHART.vermillion, opacity: 0.1 },
      });
    }

    this.opinionRadarChart.set({
      tooltip: { trigger: 'item', ...tooltipStyle },
      legend: { data: series.map(s => s.name), bottom: 0, textStyle: { color: CHART.inkMute, fontSize: 12 } },
      radar: {
        indicator: indicators,
        shape: 'polygon',
        radius: '60%',
        axisName: { color: CHART.inkMute, fontSize: 11 },
        splitLine: { lineStyle: { color: 'rgba(230,183,113,0.08)' } },
        splitArea: { show: false },
      },
      series: [{ type: 'radar', data: series }],
    });
  }

  private buildClusterChart(ticks: TickSnapshot[]) {
    const days = ticks.map(t => `T${t.ingame_day}`);
    const posSize = ticks.map(t => t.snapshot.echo_chamber_clusters![0]?.personas?.length || 0);
    const negSize = ticks.map(t => t.snapshot.echo_chamber_clusters![1]?.personas?.length || 0);
    const posOpinion = ticks.map(t => t.snapshot.echo_chamber_clusters![0]?.avg_opinion || 0);
    const negOpinion = ticks.map(t => t.snapshot.echo_chamber_clusters![1]?.avg_opinion || 0);

    this.clusterChart.set({
      tooltip: { trigger: 'axis', ...tooltipStyle },
      legend: legendCommon(['Bef\u00fcrworter (Gr\u00f6\u00dfe)', 'Skeptiker (Gr\u00f6\u00dfe)', 'Bef\u00fcrworter (Meinung)', 'Skeptiker (Meinung)']),
      grid: { top: 16, right: 16, bottom: 60, left: 44 },
      xAxis: {
        type: 'category',
        data: days,
        ...axisCommon({ splitLine: { show: false } }),
      },
      yAxis: [
        { type: 'value', name: 'Personas', ...axisCommon() },
        { type: 'value', name: 'Meinung', min: -1, max: 1, ...axisCommon(), position: 'right' as any },
      ],
      series: [
        { name: 'Bef\u00fcrworter (Gr\u00f6\u00dfe)', type: 'bar', data: posSize, itemStyle: { color: CHART.moss, opacity: 0.6 }, barWidth: '20%' },
        { name: 'Skeptiker (Gr\u00f6\u00dfe)', type: 'bar', data: negSize, itemStyle: { color: CHART.vermillion, opacity: 0.6 }, barWidth: '20%' },
        { name: 'Bef\u00fcrworter (Meinung)', type: 'line', yAxisIndex: 1, data: posOpinion, lineStyle: { color: CHART.moss, width: 2 }, itemStyle: { color: CHART.moss }, smooth: true },
        { name: 'Skeptiker (Meinung)', type: 'line', yAxisIndex: 1, data: negOpinion, lineStyle: { color: CHART.vermillion, width: 2 }, itemStyle: { color: CHART.vermillion }, smooth: true },
      ],
    });
  }
}
