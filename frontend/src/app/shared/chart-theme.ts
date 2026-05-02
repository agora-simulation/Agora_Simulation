/**
 * Mitra Chart Theme — geteilt von allen ECharts-Visualisierungen.
 * Clean, modern, Inter-Sans-Serif, abgestimmt auf die neuen Theme-Variablen.
 */

export const CHART = {
  ink:         '#0e0e0c',
  inkSoft:     '#2a2924',
  inkMute:     '#6b675c',
  inkFaint:    '#9c978a',
  paper:       '#ffffff',
  paperDeep:   '#faf7f1',
  paperEdge:   '#e3dccd',
  vermillion:  '#c8321f',
  feedbook:    '#1e3a8a',
  threadit:    '#a16207',
  moss:        '#15803d',
  rust:        '#b91c1c',
  slate:       '#5a6470',
} as const;

export const FONT_SANS = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
export const FONT_MONO = "'IBM Plex Mono', ui-monospace, monospace";

/** Standard-Tooltip — weiß mit dunkler Border, leichter Shadow */
export const tooltipStyle = {
  backgroundColor: '#ffffff',
  borderColor: CHART.ink,
  borderWidth: 1,
  borderRadius: 8,
  padding: [10, 14],
  textStyle: { color: CHART.ink, fontFamily: FONT_SANS, fontSize: 12.5, fontWeight: 500 as any },
  extraCssText: 'box-shadow: 0 4px 12px rgba(14,14,12,0.10);',
};

/** Standard-Achsen-Konfiguration */
export const axisCommon = (overrides: any = {}) => ({
  axisLine:  { lineStyle: { color: CHART.paperEdge, width: 1 } },
  axisTick:  { show: false },
  axisLabel: { color: CHART.inkMute, fontFamily: FONT_SANS, fontSize: 11, ...overrides.axisLabel },
  splitLine: { lineStyle: { color: CHART.paperEdge, type: 'dashed' as any } },
  ...overrides,
});

/**
 * Mood-Klassifizierung — geteilt von Overview, Personas, etc.
 * Erweiterte Keyword-Listen für LLM-generierte deutsche Stimmungen.
 * Rückgabe: 0=positiv, 1=neugierig, 2=neutral, 3=skeptisch, 4=negativ
 */
const MOOD_POSITIVE = [
  'positiv', 'begeistert', 'froh', 'zufrieden', 'optimistisch', 'erfreut',
  'glücklich', 'gluecklich', 'fröhlich', 'froehlich', 'beeindruckt',
  'aufgeschlossen', 'hoffnungsvoll', 'enthusiastisch', 'überzeugt', 'ueberzeugt',
  'motiviert', 'angetan', 'wohlwollend', 'euphorisch', 'dankbar', 'ermutigt',
  'bestärkt', 'bestaerkt', 'unterstützend', 'unterstuetzend', 'freundlich',
  'warmherzig', 'gelöst', 'geloest', 'heiter', 'beschwingt',
];
const MOOD_CURIOUS = [
  'neugier', 'interessiert', 'gespannt', 'aufmerksam', 'wissbegierig',
  'offen', 'fasziniert', 'lernbereit', 'aufnahmebereit', 'angeregt',
  'inspiriert', 'nachdenklich',
];
const MOOD_SKEPTIC = [
  'skepti', 'kritisch', 'misstrauisch', 'zweifel', 'vorsichtig',
  'zurückhaltend', 'zurueckhaltend', 'abwartend', 'unsicher', 'argwöhnisch',
  'argwoehnisch', 'hinterfragend', 'distanziert', 'reserviert', 'wachsam',
  'bedenken', 'unentschlossen', 'zögerlich', 'zoegerlich', 'ablehnend',
  'missbilligend', 'zwiegespalten',
];
const MOOD_NEGATIVE = [
  'negativ', 'genervt', 'frustr', 'wüt', 'wut', 'verärgert', 'veraergert',
  'ärgerlich', 'aergerlich', 'enttäuscht', 'enttaeuscht', 'empört', 'empoert',
  'sauer', 'gereizt', 'aufgebracht', 'feindsel', 'abgeneigt', 'entrüstet',
  'entruestet', 'unzufrieden', 'besorgt', 'verängstigt', 'veraengstigt',
  'pessimistisch', 'resigniert', 'verbittert', 'wütend', 'wuetend',
  'aggressiv', 'feindselig', 'ablehn',
];

export function classifyMoodIndex(mood: string): number {
  if (!mood) return 2;
  const m = mood.toLowerCase();
  if (MOOD_POSITIVE.some(k => m.includes(k))) return 0;
  if (MOOD_CURIOUS.some(k => m.includes(k))) return 1;
  if (MOOD_SKEPTIC.some(k => m.includes(k))) return 3;
  if (MOOD_NEGATIVE.some(k => m.includes(k))) return 4;
  return 2;
}

export type MoodCategory = 'positiv' | 'neugierig' | 'neutral' | 'skeptisch' | 'negativ';
const MOOD_CATEGORIES: MoodCategory[] = ['positiv', 'neugierig', 'neutral', 'skeptisch', 'negativ'];

export function classifyMood(mood: string | undefined): MoodCategory {
  return MOOD_CATEGORIES[classifyMoodIndex(mood || '')];
}

const MOOD_COLORS = [CHART.moss, CHART.feedbook, CHART.inkMute, CHART.threadit, CHART.vermillion];

export function getMoodColor(mood: string | undefined): string {
  return MOOD_COLORS[classifyMoodIndex(mood || '')];
}

/** Standard-Legende */
export const legendCommon = (data: string[]) => ({
  data,
  bottom: 0,
  textStyle: { color: CHART.inkMute, fontFamily: FONT_SANS, fontSize: 12 },
  itemWidth: 10,
  itemHeight: 10,
  icon: 'circle',
});
