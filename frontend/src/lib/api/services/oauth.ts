import { BaseAPI } from "../client";
import type {
  OAuthClient,
  OAuthClientCreateData,
  OAuthClientUpdateData,
  OAuthClientsResponse,
  OAuthClientResponse,
} from "@/types";

class OAuthService extends BaseAPI {
  async listClients(): Promise<OAuthClientsResponse> {
    return this.get<OAuthClientsResponse>("/api/oauth-clients");
  }

  async getClient(id: number): Promise<OAuthClientResponse> {
    return this.get<OAuthClientResponse>(`/api/oauth-clients/${id}`);
  }

  async createClient(data: OAuthClientCreateData): Promise<OAuthClientResponse> {
    return this.post<OAuthClientResponse>("/api/oauth-clients", data);
  }

  async updateClient(
    id: number,
    data: OAuthClientUpdateData
  ): Promise<OAuthClientResponse> {
    return this.patch<OAuthClientResponse>(`/api/oauth-clients/${id}`, data);
  }

  async deleteClient(id: number): Promise<{ success: boolean; deleted_id: number }> {
    return this.delete<{ success: boolean; deleted_id: number }>(
      `/api/oauth-clients/${id}`
    );
  }

  async regenerateSecret(id: number): Promise<OAuthClientResponse> {
    return this.post<OAuthClientResponse>(
      `/api/oauth-clients/${id}/regenerate-secret`,
      {}
    );
  }
}

export const oauthService = new OAuthService();
