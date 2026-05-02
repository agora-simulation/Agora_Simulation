import { Component, inject, signal, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { DecimalPipe, DatePipe } from '@angular/common';
import { ScrollingModule } from '@angular/cdk/scrolling';
import { NgxEchartsDirective, provideEchartsCore } from 'ngx-echarts';
import { EChartsOption } from 'echarts';
import * as echarts from 'echarts';
import { PersonaService } from '../../../core/services/persona.service';
import { Persona, ChatMessage, Conversation } from '../../../core/models/persona.model';
import { CHART, tooltipStyle, classifyMood as classifyMoodShared, getMoodColor as getMoodColorShared } from '../../../shared/chart-theme';
import type { MoodCategory } from '../../../shared/chart-theme';

export type SortKey = 'name' | 'mood' | 'skeptic' | 'reach';
export type MoodKey = MoodCategory;

@Component({
  selector: 'app-personas',
  standalone: true,
  imports: [FormsModule, ScrollingModule, NgxEchartsDirective, DecimalPipe, DatePipe],
  providers: [provideEchartsCore({ echarts })],
  templateUrl: './personas.component.html',
})
export class PersonasComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private personaService = inject(PersonaService);

  personas = signal<Persona[]>([]);
  filteredPersonas = signal<Persona[]>([]);
  selectedPersona = signal<Persona | null>(null);
  loading = signal(true);
  searchTerm = signal('');
  showSkepticsOnly = signal(false);

  sortKey = signal<SortKey>('name');
  activeMoods = signal<Set<MoodKey>>(new Set());

  readonly sortOptions: { key: SortKey; label: string }[] = [
    { key: 'name', label: 'Name (A–Z)' },
    { key: 'mood', label: 'Stimmung' },
    { key: 'skeptic', label: 'Skeptiker zuerst' },
    { key: 'reach', label: 'Reichweite' },
  ];

  readonly moodOptions: { key: MoodKey; label: string }[] = [
    { key: 'positiv', label: 'positiv' },
    { key: 'negativ', label: 'negativ' },
    { key: 'skeptisch', label: 'skeptisch' },
    { key: 'neugierig', label: 'neugierig' },
    { key: 'neutral', label: 'neutral' },
  ];

  showChat = signal(false);
  chatMessages = signal<ChatMessage[]>([]);
  chatInput = signal('');
  chatLoading = signal(false);

  radarChart = signal<EChartsOption>({});
  showRadar = signal(false);
  conversations = signal<Conversation[]>([]);
  activeConversationId = signal<string | null>(null);
  conversationsLoading = signal(false);

  readonly bigFiveTraits = [
    { key: 'openness', label: 'Offenheit' },
    { key: 'conscientiousness', label: 'Gewissenhaftigkeit' },
    { key: 'extraversion', label: 'Extraversion' },
    { key: 'agreeableness', label: 'Verträglichkeit' },
    { key: 'neuroticism', label: 'Neurotizismus' },
  ];

  private simId = '';

  ngOnInit() {
    this.simId = this.route.parent!.snapshot.params['id'];
    this.personaService.list(this.simId, { limit: 200 }).subscribe(res => {
      this.personas.set(res.items);
      this.applyFilter();
      this.loading.set(false);
    });
  }

  applyFilter() {
    let result = this.personas().slice();

    if (this.searchTerm()) {
      const term = this.searchTerm().toLowerCase();
      result = result.filter(p =>
        p.name.toLowerCase().includes(term) ||
        (p.location || '').toLowerCase().includes(term) ||
        (p.occupation || '').toLowerCase().includes(term)
      );
    }

    if (this.showSkepticsOnly()) {
      result = result.filter(p => p.is_skeptic);
    }

    const moods = this.activeMoods();
    if (moods.size > 0) {
      result = result.filter(p => {
        const cat = this.classifyMood(p.current_state?.mood);
        return moods.has(cat);
      });
    }

    result.sort((a, b) => this.compare(a, b, this.sortKey()));
    this.filteredPersonas.set(result);
  }

  toggleMood(m: MoodKey) {
    const next = new Set(this.activeMoods());
    if (next.has(m)) next.delete(m); else next.add(m);
    this.activeMoods.set(next);
    this.applyFilter();
  }

  isMoodActive(m: MoodKey): boolean {
    return this.activeMoods().has(m);
  }

  setSort(key: SortKey) {
    this.sortKey.set(key);
    this.applyFilter();
  }

  clearFilters() {
    this.searchTerm.set('');
    this.showSkepticsOnly.set(false);
    this.activeMoods.set(new Set());
    this.applyFilter();
  }

  hasActiveFilters(): boolean {
    return !!this.searchTerm() || this.showSkepticsOnly() || this.activeMoods().size > 0;
  }

  activeFilterCount(): number {
    let n = 0;
    if (this.searchTerm()) n++;
    if (this.showSkepticsOnly()) n++;
    n += this.activeMoods().size;
    return n;
  }

  private compare(a: Persona, b: Persona, key: SortKey): number {
    switch (key) {
      case 'name':
        return a.name.localeCompare(b.name);
      case 'mood': {
        const am = (a.current_state?.mood || '').toLowerCase();
        const bm = (b.current_state?.mood || '').toLowerCase();
        return am.localeCompare(bm) || a.name.localeCompare(b.name);
      }
      case 'skeptic': {
        const av = a.is_skeptic ? 0 : 1;
        const bv = b.is_skeptic ? 0 : 1;
        return av - bv || a.name.localeCompare(b.name);
      }
      case 'reach': {
        const ar = a.social_connections?.length ?? 0;
        const br = b.social_connections?.length ?? 0;
        return br - ar || a.name.localeCompare(b.name);
      }
    }
  }

  private classifyMood(mood: string | undefined): MoodKey {
    return classifyMoodShared(mood);
  }

  selectPersona(p: Persona) {
    this.selectedPersona.set(p);
    this.showChat.set(false);
    this.chatMessages.set([]);
    this.buildRadarChart(p);
    this.loadConversations(p.id);
  }

  clearSelection() {
    this.selectedPersona.set(null);
    this.showChat.set(false);
    this.chatMessages.set([]);
  }

  openChat() {
    this.showChat.set(true);
    this.activeConversationId.set(null); // kein persistiertes Gespräch
  }

  getMoodColor(mood: string | undefined): string {
    return getMoodColorShared(mood);
  }

  initials(name: string): string {
    if (!name) return '?';
    const parts = name.trim().split(/\s+/);
    if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
    return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
  }

  buildRadarChart(persona: Persona) {
    const dims = persona.current_state?.opinion_dimensions;
    if (!dims) {
      this.showRadar.set(false);
      return;
    }
    const indicators = [
      { name: 'Qualität', max: 1 },
      { name: 'Preis', max: 1 },
      { name: 'Vertrauen', max: 1 },
      { name: 'Innovation', max: 1 },
      { name: 'Ethik', max: 1 },
      { name: 'Sozial', max: 1 },
      { name: 'Relevanz', max: 1 },
    ];
    // Werte auf 0-1 normalisieren (von -1..1 auf 0..1)
    const values = [
      dims.product_quality,
      dims.price_fairness,
      dims.brand_trust,
      dims.innovation,
      dims.ethical_concerns,
      dims.social_proof,
      dims.personal_relevance,
    ].map(v => Math.round(((v + 1) / 2) * 100) / 100);

    this.radarChart.set({
      tooltip: { trigger: 'item', ...tooltipStyle },
      radar: {
        indicator: indicators,
        shape: 'polygon',
        radius: '65%',
        axisName: { color: '#6b6b63', fontSize: 11 },
        splitLine: { lineStyle: { color: 'rgba(0,0,0,0.08)' } },
        splitArea: { show: false },
      },
      series: [{
        type: 'radar',
        data: [{
          value: values,
          name: 'Meinung',
          itemStyle: { color: CHART.feedbook },
          lineStyle: { color: CHART.feedbook, width: 2 },
          areaStyle: { color: CHART.feedbook, opacity: 0.15 },
        }],
      }],
    });
    this.showRadar.set(true);
  }

  loadConversations(personaId: string) {
    this.conversationsLoading.set(true);
    this.personaService.listConversations(personaId).subscribe({
      next: (convs) => {
        this.conversations.set(convs);
        this.conversationsLoading.set(false);
      },
      error: () => this.conversationsLoading.set(false),
    });
  }

  startNewConversation() {
    const persona = this.selectedPersona();
    if (!persona) return;
    this.personaService.startConversation(persona.id).subscribe(res => {
      this.activeConversationId.set(res.conversation_id);
      this.chatMessages.set([]);
      this.showChat.set(true);
    });
  }

  loadConversationHistory(conv: Conversation) {
    const persona = this.selectedPersona();
    if (!persona) return;
    this.personaService.getConversation(persona.id, conv.conversation_id).subscribe(detail => {
      this.chatMessages.set(detail.messages);
      this.activeConversationId.set(conv.conversation_id);
      this.showChat.set(true);
    });
  }

  sendMessage() {
    const msg = this.chatInput().trim();
    if (!msg || this.chatLoading()) return;
    const persona = this.selectedPersona();
    if (!persona) return;

    this.chatMessages.update(msgs => [...msgs, { role: 'user' as const, content: msg }]);
    this.chatInput.set('');
    this.chatLoading.set(true);

    const request: any = { messages: this.chatMessages() };
    if (this.activeConversationId()) {
      request.conversation_id = this.activeConversationId();
    }

    this.personaService.chat(persona.id, request).subscribe({
      next: (res) => {
        this.chatMessages.update(msgs => [...msgs, { role: 'assistant' as const, content: res.response }]);
        this.chatLoading.set(false);
      },
      error: () => {
        this.chatMessages.update(msgs => [...msgs, { role: 'assistant' as const, content: 'Fehler bei der Kommunikation.' }]);
        this.chatLoading.set(false);
      },
    });
  }

  // Big Five helpers
  getTraitValue(persona: Persona, key: string): number {
    return (persona.personality_traits as any)?.[key] ?? 0.5;
  }

  getTraitColor(val: number): string {
    if (val > 0.7) return CHART.moss;
    if (val > 0.4) return CHART.feedbook;
    return CHART.inkMute;
  }

  // Memory helpers
  sortedMemories(persona: Persona) {
    return [...(persona.memory || [])].sort((a, b) => b.emotional_weight - a.emotional_weight).slice(0, 8);
  }

  memTypeLabel(type: string): string {
    const map: Record<string, string> = {
      conflict: 'Konflikt', persuasion: 'Überzeugung',
      social: 'Sozial', surprise: 'Überraschung', personal: 'Persönlich',
    };
    return map[type] || type;
  }

  weightLabel(w: number): string {
    if (w >= 0.7) return '★★★';
    if (w >= 0.4) return '★★';
    return '★';
  }

  // Demografie helpers
  incomeLabel(val: string): string {
    const map: Record<string, string> = {
      niedrig: 'Niedrigeinkommen', mittel: 'Mitteleinkommen',
      hoch: 'Hoheinkommen', sehr_hoch: 'Sehr hohes Einkommen',
    };
    return map[val] || val;
  }

  familyLabel(val: string): string {
    const map: Record<string, string> = {
      single: 'Single', partnerschaft: 'Partnerschaft',
      familie_klein: 'Familie (klein)', familie_gross: 'Familie (groß)',
      alleinerziehend: 'Alleinerziehend', rentner: 'Rentner',
    };
    return map[val] || val;
  }
}
