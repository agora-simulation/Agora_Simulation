/**
 * Agora Chart Theme — geteilt von allen ECharts-Visualisierungen.
 * Supports dark and light themes via getChartColors().
 */

export interface ChartColors {
  ink: string;
  inkSoft: string;
  inkMute: string;
  inkFaint: string;
  paper: string;
  paperDeep: string;
  paperEdge: string;
  vermillion: string;
  feedbook: string;
  threadit: string;
  moss: string;
  rust: string;
  slate: string;
}

const DARK_COLORS: ChartColors = {
  ink:         '#f7efe3',
  inkSoft:     '#e8dac6',
  inkMute:     '#c4a882',
  inkFaint:    '#9a8468',
  paper:       '#1e1610',
  paperDeep:   '#0c0a08',
  paperEdge:   '#2e2419',
  vermillion:  '#e05a4a',
  feedbook:    '#5a9fd6',
  threadit:    '#e6a040',
  moss:        '#4aba7a',
  rust:        '#e05a4a',
  slate:       '#c4a882',
};

const LIGHT_COLORS: ChartColors = {
  ink:         '#2c2418',
  inkSoft:     '#4a3f32',
  inkMute:     '#7a6b58',
  inkFaint:    '#a89880',
  paper:       '#f5eed8',
  paperDeep:   '#ece4d4',
  paperEdge:   '#e6dcca',
  vermillion:  '#c8321f',
  feedbook:    '#2a7ab8',
  threadit:    '#c47a10',
  moss:        '#15803d',
  rust:        '#c8321f',
  slate:       '#7a6b58',
};

/** Returns theme-appropriate chart colors */
export function getChartColors(isDark: boolean): ChartColors {
  return isDark ? DARK_COLORS : LIGHT_COLORS;
}

/** Legacy static export — defaults to dark for backward compat */
export const CHART = DARK_COLORS;

export const FONT_SANS = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
export const FONT_MONO = "'IBM Plex Mono', ui-monospace, monospace";

/** Theme-aware tooltip style */
export function getTooltipStyle(isDark: boolean) {
  const c = getChartColors(isDark);
  return {
    backgroundColor: c.paper,
    borderColor: isDark ? 'rgba(230, 183, 113, 0.2)' : 'rgba(120, 95, 55, 0.15)',
    borderWidth: 1,
    borderRadius: 8,
    padding: [10, 14],
    textStyle: { color: c.ink, fontFamily: FONT_SANS, fontSize: 13, fontWeight: 500 as any },
    extraCssText: isDark
      ? 'box-shadow: 0 4px 12px rgba(0,0,0,0.35);'
      : 'box-shadow: 0 4px 12px rgba(120,95,55,0.12);',
  };
}

/** Legacy static export */
export const tooltipStyle = getTooltipStyle(true);

/** Theme-aware axis configuration */
export function getAxisCommon(isDark: boolean, overrides: any = {}) {
  const c = getChartColors(isDark);
  return {
    axisLine:  { lineStyle: { color: c.paperEdge, width: 1 } },
    axisTick:  { show: false },
    axisLabel: { color: c.inkMute, fontFamily: FONT_SANS, fontSize: 11, ...overrides.axisLabel },
    splitLine: { lineStyle: {
      color: isDark ? 'rgba(230, 183, 113, 0.08)' : 'rgba(120, 95, 55, 0.08)',
      type: 'dashed' as any,
    }},
    ...overrides,
  };
}

/** Legacy static export */
export const axisCommon = (overrides: any = {}) => getAxisCommon(true, overrides);

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

/** Theme-aware mood colors */
export function getMoodColors(isDark: boolean): string[] {
  const c = getChartColors(isDark);
  return [c.moss, c.feedbook, c.inkMute, c.threadit, c.vermillion];
}

/** Legacy — defaults to dark */
export function getMoodColor(mood: string | undefined): string {
  const MOOD_COLORS = [CHART.moss, CHART.feedbook, CHART.inkMute, CHART.threadit, CHART.vermillion];
  return MOOD_COLORS[classifyMoodIndex(mood || '')];
}

/** Theme-aware mood color */
export function getMoodColorThemed(mood: string | undefined, isDark: boolean): string {
  return getMoodColors(isDark)[classifyMoodIndex(mood || '')];
}

/** Standard-Legende */
export function getLegendCommon(isDark: boolean, data: string[]) {
  const c = getChartColors(isDark);
  return {
    data,
    bottom: 0,
    textStyle: { color: c.inkMute, fontFamily: FONT_SANS, fontSize: 12 },
    itemWidth: 10,
    itemHeight: 10,
    icon: 'circle',
  };
}

/** Legacy */
export const legendCommon = (data: string[]) => getLegendCommon(true, data);
