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
}

export const componentService = new ComponentService();
