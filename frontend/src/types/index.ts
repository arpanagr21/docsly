// User types
export interface User {
  id: number;
  email: string;
  created_at: string;
}

// Block types
export interface Block {
  type: "markdown" | "component";
  content?: string;
  name?: string;
  props?: Record<string, unknown>;
}

// Document types
export interface DocumentContent {
  version: number | string;
  theme_id: number | null;
  markdown: string;
  blocks?: Block[];
}

export interface Document {
  id: number;
  user_id: number;
  title: string;
  content: DocumentContent;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface CreateDocumentData {
  title: string;
  content?: DocumentContent;
  metadata?: Record<string, unknown>;
}

export interface UpdateDocumentData {
  title?: string;
  content?: DocumentContent;
  metadata?: Record<string, unknown>;
}

// JSON Schema structure
export interface JSONSchema {
  type: "object";
  properties: Record<string, { type: string; [key: string]: unknown }>;
  required?: string[];
}

// Component types
export interface Component {
  id: number;
  user_id: number | null;
  name: string;
  version: string;
  schema: JSONSchema;
  template: string;
  is_active: boolean;
  is_builtin: boolean;
  created_at?: string;
}

export interface ComponentCreateData {
  name: string;
  schema: JSONSchema;
  template: string;
}

export interface ComponentUpdateData {
  name?: string;
  schema?: JSONSchema;
  template?: string;
}

// Theme types
export interface ThemeVariables {
  [key: string]:
    | string
    | number
    | Record<string, string | number | Record<string, string | number>>;
}

export interface Theme {
  id: number;
  user_id: number | null;
  name: string;
  variables: ThemeVariables;
  is_default: boolean;
  is_builtin: boolean;
  created_at?: string;
}

export interface ThemeCreateData {
  name: string;
  variables: ThemeVariables;
  is_default?: boolean;
}

export interface ThemeUpdateData {
  name?: string;
  variables?: ThemeVariables;
  is_default?: boolean;
}

// Auth types
export interface AuthResponse {
  user: User;
  access_token: string;
  refresh_token: string;
}

export interface LoginData {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
}

// API Response types
export interface DocumentsResponse {
  documents: Document[];
}

export interface DocumentResponse {
  document: Document;
}

export interface RenderResponse {
  html: string;
}

export interface ComponentsResponse {
  components: Component[];
}

export interface ComponentResponse {
  component: Component;
}

export interface ThemesResponse {
  themes: Theme[];
}

export interface ThemeResponse {
  theme: Theme;
}

export interface UserResponse {
  user: User;
}

export interface RefreshResponse {
  access_token: string;
}

export interface ApiError {
  error: string;
  message?: string;
}
