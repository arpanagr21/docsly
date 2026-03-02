// User types
export interface User {
  id: number;
  email: string;
  created_at: string;
}

// Block types
export interface Block {
  id?: string;
  type: "markdown" | "component";
  content?: string;
  name?: string;
  version?: number;
  slot?: string;
  props?: Record<string, unknown>;
  inner_markdown?: string;
  children?: Block[];
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
  style_contract?: Record<string, unknown>;
  default_styles?: Record<string, unknown>;
  is_active: boolean;
  is_builtin: boolean;
  created_at?: string;
}

export interface ComponentCreateData {
  name: string;
  schema: JSONSchema;
  template: string;
  style_contract?: Record<string, unknown>;
  default_styles?: Record<string, unknown>;
}

export interface ComponentUpdateData {
  name?: string;
  schema?: JSONSchema;
  template?: string;
  style_contract?: Record<string, unknown>;
  default_styles?: Record<string, unknown>;
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

// OAuth Client types
export interface OAuthClient {
  id: number;
  user_id: number;
  name: string;
  client_id: string;
  client_secret?: string; // Only returned on creation or regeneration
  scopes: string;
  is_active: boolean;
  created_at: string | null;
  last_used_at: string | null;
  _notice?: string;
}

export interface OAuthClientCreateData {
  name: string;
  scopes?: string;
}

export interface OAuthClientUpdateData {
  name?: string;
  is_active?: boolean;
}

export interface OAuthClientsResponse {
  clients: OAuthClient[];
}

export interface OAuthClientResponse {
  client: OAuthClient;
}
