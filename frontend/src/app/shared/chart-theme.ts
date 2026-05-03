/**
 * Agora Chart Theme — geteilt von allen ECharts-Visualisierungen.
 * Clean, modern, Inter-Sans-Serif, abgestimmt auf die neuen Theme-Variablen.
 */

export const CHART = {
  ink:         '#f4e8d4',
  inkSoft:     '#e0d0b8',
  inkMute:     '#a89171',
  inkFaint:    '#7a6850',
  paper:       '#1e1610',
  paperDeep:   '#0c0a08',
  paperEdge:   '#2e2419',
  vermillion:  '#e05a4a',
  feedbook:    '#5a9fd6',
  threadit:    '#e6a040',
  moss:        '#4aba7a',
  rust:        '#e05a4a',
  slate:       '#a89171',
} as const;

export const FONT_SANS = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
export const FONT_MONO = "'IBM Plex Mono', ui-monospace, monospace";

/** Standard-Tooltip �� dunkler Hintergrund mit warmem Border */
export const tooltipStyle = {
  backgroundColor: '#1e1610',
  borderColor: 'rgba(230, 183, 113, 0.2)',
  borderWidth: 1,
  borderRadius: 8,
  padding: [10, 14],
  textStyle: { color: '#f4e8d4', fontFamily: FONT_SANS, fontSize: 12.5, fontWeight: 500 as any },
  extraCssText: 'box-shadow: 0 4px 12px rgba(0,0,0,0.35);',
};

/** Standard-Achsen-Konfiguration */
export const axisCommon = (overrides: any = {}) => ({
  axisLine:  { lineStyle: { color: CHART.paperEdge, width: 1 } },
  axisTick:  { show: false },
  axisLabel: { color: CHART.inkMute, fontFamily: FONT_SANS, fontSize: 11, ...overrides.axisLabel },
  splitLine: { lineStyle: { color: 'rgba(230, 183, 113, 0.08)', type: 'dashed' as any } },
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
