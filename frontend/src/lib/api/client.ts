const ACCESS_TOKEN_KEY = "access_token";

export class BaseAPI {
  protected baseUrl =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000";

  protected getAccessToken(): string | null {
    if (typeof window === "undefined") {
      return null;
    }
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  }

  protected async request<T>(
    path: string,
    options?: RequestInit
  ): Promise<T> {
    const token = this.getAccessToken();
    const headers: HeadersInit = {
      "Content-Type": "application/json",
      ...options?.headers,
    };

    if (token) {
      (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      // Clear token and redirect to login
      if (typeof window !== "undefined") {
        localStorage.removeItem(ACCESS_TOKEN_KEY);
        localStorage.removeItem("refresh_token");
        window.location.href = "/login";
      }
      throw new Error("Unauthorized");
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: "An error occurred" }));
      throw new Error(error.error || error.message || `HTTP error! status: ${response.status}`);
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return response.json();
  }

  protected async get<T>(path: string): Promise<T> {
    return this.request<T>(path, { method: "GET" });
  }

  protected async post<T>(path: string, data?: unknown): Promise<T> {
    return this.request<T>(path, {
      method: "POST",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  protected async put<T>(path: string, data?: unknown): Promise<T> {
    return this.request<T>(path, {
      method: "PUT",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  protected async delete<T>(path: string): Promise<T> {
    return this.request<T>(path, { method: "DELETE" });
  }

  protected async patch<T>(path: string, data?: unknown): Promise<T> {
    return this.request<T>(path, {
      method: "PATCH",
      body: data ? JSON.stringify(data) : undefined,
    });
  }
}
