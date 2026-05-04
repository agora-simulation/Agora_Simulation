export type TemplateCategory = 'distribution' | 'tonality' | 'trigger_library' | 'research';

export interface Template {
  id: string;
  category: TemplateCategory;
  name: string;
  owner_id: string | null;
  is_default: boolean;
  content: Record<string, any>;
  version: number;
  parent_id: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface TemplateCreate {
  category: TemplateCategory;
  name: string;
  content: Record<string, any>;
  is_default?: boolean;
  parent_id?: string;
}
