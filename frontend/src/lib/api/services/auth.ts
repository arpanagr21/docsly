import { BaseAPI } from "../client";
import type {
  AuthResponse,
  UserResponse,
  RefreshResponse,
} from "@/types";

class AuthService extends BaseAPI {
  async login(email: string, password: string): Promise<AuthResponse> {
    const response = await this.post<AuthResponse>("/api/auth/login", {
      email,
      password,
    });

    // Store tokens
    if (typeof window !== "undefined") {
      localStorage.setItem("access_token", response.access_token);
      localStorage.setItem("refresh_token", response.refresh_token);
    }

    return response;
  }

  async register(email: string, password: string): Promise<AuthResponse> {
    const response = await this.post<AuthResponse>("/api/auth/register", {
      email,
      password,
    });

    // Store tokens
    if (typeof window !== "undefined") {
      localStorage.setItem("access_token", response.access_token);
      localStorage.setItem("refresh_token", response.refresh_token);
    }

    return response;
  }

  async refresh(): Promise<RefreshResponse> {
    const refreshToken =
      typeof window !== "undefined"
        ? localStorage.getItem("refresh_token")
        : null;

    const response = await this.post<RefreshResponse>("/api/auth/refresh", {
      refresh_token: refreshToken,
    });

    // Update access token
    if (typeof window !== "undefined") {
      localStorage.setItem("access_token", response.access_token);
    }

    return response;
  }

  async me(): Promise<UserResponse> {
    return this.get<UserResponse>("/api/auth/me");
  }

  logout(): void {
    if (typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
    }
  }
}

export const authService = new AuthService();
