export interface PersonaMemory {
  tick: number;
  type: 'conflict' | 'persuasion' | 'social' | 'surprise' | 'personal';
  summary: string;
  emotional_weight: number;
}

export interface PersonaTraits {
  openness: number;
  conscientiousness: number;
  extraversion: number;
  agreeableness: number;
  neuroticism: number;
}

export interface OpinionDimensions {
  product_quality: number;
  price_fairness: number;
  brand_trust: number;
  innovation: number;
  ethical_concerns: number;
  social_proof: number;
  personal_relevance: number;
}

// v1.1 Actor Types
export type ActorType = 'private_person' | 'company' | 'research_institute' | 'authority' | 'media' | 'influencer' | 'expert' | 'collective' | 'validator';

export type FunctionTag = 'meinungs_gatekeeper' | 'marktzugangs_gatekeeper' | 'bruckenakteur' | 'multiplikator' | 'polarisierer' | 'early_signal_giver';

export type Traegerschaft = 'privat' | 'oeffentlich' | 'genossenschaftlich' | 'gemischt' | 'kommunal';

export type PersonContext = 'privat' | 'beruflich' | 'oeffentlich';
export type InfluencerContext = 'consumer' | 'business' | 'politisch';

// Keep PersonaType for backwards compatibility
export type PersonaType = 'individual' | 'organization' | 'institution' | 'politician';

export interface Persona {
  id: string;
  simulation_id: string;
  name: string;
  age: string | null;
  location: string | null;
  occupation: string | null;
  personality: string | null;
  values: string[];
  communication_style: string | null;
  initial_opinion: string | null;
  is_skeptic: boolean;
  persona_type?: PersonaType;
  entity_subtype?: string | null;
  social_connections: string[];
  current_state: PersonaState;
  created_at: string;
  memory?: PersonaMemory[];
  personality_traits?: PersonaTraits;
  education_level?: string | null;
  income_bracket?: string | null;
  family_status?: string | null;
  political_leaning?: string | null;
  tech_affinity?: number | null;
  // v1.1 fields
  actor_type?: ActorType;
  subtype?: string | null;
  context?: PersonContext | InfluencerContext | null;
  traegerschaft?: Traegerschaft | null;
  stance?: string | null;
  activation_latency?: number;
  trigger_condition?: Record<string, any> | null;
  function_tags?: FunctionTag[];
  engagement_decay_rate?: number;
  profile_data?: Record<string, any>;
}

export interface PersonaState {
  opinion_evolution?: string;
  mood?: string;
  recent_actions?: RecentAction[];
  platform_affinity?: Record<string, number>;
  connection_strength?: Record<string, number>;
  opinion_dimensions?: OpinionDimensions;
}

export interface RecentAction {
  tick: number;
  summary: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatRequest {
  messages: ChatMessage[];
  conversation_id?: string;
}

export interface ChatResponse {
  response: string;
  persona_id: string;
}

export interface Conversation {
  conversation_id: string;
  persona_id: string;
  message_count: number;
  summary?: string;
  preview?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ConversationDetail extends Conversation {
  messages: ChatMessage[];
}

export const ACTOR_TYPE_LABELS: Record<ActorType, string> = {
  private_person: 'Privatperson',
  company: 'Firma',
  research_institute: 'Institut/Forschung',
  authority: 'Behörde/Regulator',
  media: 'Medium/Journalist',
  influencer: 'Influencer',
  expert: 'Experte/Fachperson',
  collective: 'Kollektiver Akteur',
  validator: 'Validierer/Zertifizierer',
};

export const ACTOR_TYPE_ICONS: Record<ActorType, string> = {
  private_person: 'pi pi-user',
  company: 'pi pi-building',
  research_institute: 'pi pi-search',
  authority: 'pi pi-shield',
  media: 'pi pi-megaphone',
  influencer: 'pi pi-star',
  expert: 'pi pi-briefcase',
  collective: 'pi pi-users',
  validator: 'pi pi-check-circle',
};

export const ACTOR_TYPE_COLORS: Record<ActorType, string> = {
  private_person: '#6366f1',
  company: '#f59e0b',
  research_institute: '#10b981',
  authority: '#ef4444',
  media: '#8b5cf6',
  influencer: '#ec4899',
  expert: '#06b6d4',
  collective: '#f97316',
  validator: '#14b8a6',
};
