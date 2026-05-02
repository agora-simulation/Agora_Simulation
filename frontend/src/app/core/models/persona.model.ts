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
