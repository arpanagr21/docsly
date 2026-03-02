import { BaseAPI } from "../client";
import type {
  Block,
  ComponentCreateData,
  ComponentUpdateData,
  ComponentsResponse,
  ComponentResponse,
} from "@/types";

export interface PreviewResponse {
  html: string;
  meta?: {
    interpolated_markdown?: string;
    rendered_tags?: string[];
    markdown_outline?: Array<{ type: string; tag: string; level: number }>;
    token_types?: string[];
    inline_tags?: string[];
    element_selectors?: string[];
    styled_rendered_tags?: string[];
    unstyled_rendered_tags?: string[];
    placeholders?: string[];
    unresolved_placeholders?: string[];
    contract_slots?: string[];
    declared_slots?: string[];
    undeclared_slots?: string[];
    extra_slots?: string[];
    contract_variants?: string[];
    declared_variants?: string[];
    undeclared_variants?: string[];
    extra_variants?: string[];
  };
}

class ComponentService extends BaseAPI {
  async list(): Promise<ComponentsResponse> {
    return super.get<ComponentsResponse>("/api/components");
  }

  async getById(id: number): Promise<ComponentResponse> {
    return super.get<ComponentResponse>(`/api/components/${id}`);
  }

  async getByName(name: string): Promise<ComponentResponse> {
    return super.get<ComponentResponse>(
      `/api/components/name/${encodeURIComponent(name)}`
    );
  }

  async create(data: ComponentCreateData): Promise<ComponentResponse> {
    return super.post<ComponentResponse>("/api/components", data);
  }

  async update(
    id: number,
    data: ComponentUpdateData
  ): Promise<ComponentResponse> {
    return super.put<ComponentResponse>(`/api/components/${id}`, data);
  }

  async remove(id: number): Promise<void> {
    return super.delete<void>(`/api/components/${id}`);
  }

  async previewBlock(block: Block): Promise<PreviewResponse> {
    return super.post<PreviewResponse>("/api/components/preview", block);
  }

  async previewTemplate(
    name: string,
    template: string,
    props: Record<string, unknown>,
    styleContract: Record<string, unknown>,
    defaultStyles: Record<string, unknown>
  ): Promise<PreviewResponse> {
    return super.post<PreviewResponse>("/api/components/preview-template", {
      name,
      template,
      props,
      style_contract: styleContract,
      default_styles: defaultStyles,
    });
  }
}

export const componentService = new ComponentService();
