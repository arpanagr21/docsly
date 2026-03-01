import { BaseAPI } from "../client";
import type {
  ThemeCreateData,
  ThemeUpdateData,
  ThemesResponse,
  ThemeResponse,
} from "@/types";

class ThemeService extends BaseAPI {
  async list(): Promise<ThemesResponse> {
    return super.get<ThemesResponse>("/api/themes");
  }

  async getById(id: number): Promise<ThemeResponse> {
    return super.get<ThemeResponse>(`/api/themes/${id}`);
  }

  async create(data: ThemeCreateData): Promise<ThemeResponse> {
    return super.post<ThemeResponse>("/api/themes", data);
  }

  async update(id: number, data: ThemeUpdateData): Promise<ThemeResponse> {
    return super.put<ThemeResponse>(`/api/themes/${id}`, data);
  }

  async remove(id: number): Promise<void> {
    return super.delete<void>(`/api/themes/${id}`);
  }
}

export const themeService = new ThemeService();
