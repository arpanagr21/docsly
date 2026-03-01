import { BaseAPI } from "../client";
import type {
  Document,
  DocumentContent,
  DocumentsResponse,
  DocumentResponse,
  RenderResponse,
} from "@/types";

class DocumentService extends BaseAPI {
  async list(): Promise<DocumentsResponse> {
    return super.get<DocumentsResponse>("/api/documents");
  }

  async getById(id: number): Promise<DocumentResponse> {
    return super.get<DocumentResponse>(`/api/documents/${id}`);
  }

  async create(data: {
    title: string;
    content?: DocumentContent;
  }): Promise<DocumentResponse> {
    return super.post<DocumentResponse>("/api/documents", data);
  }

  async update(
    id: number,
    data: Partial<Document>
  ): Promise<DocumentResponse> {
    return super.put<DocumentResponse>(`/api/documents/${id}`, data);
  }

  async remove(id: number): Promise<void> {
    return super.delete<void>(`/api/documents/${id}`);
  }

  async render(id: number): Promise<RenderResponse> {
    return super.get<RenderResponse>(`/api/documents/${id}/render`);
  }

  async preview(content: DocumentContent): Promise<RenderResponse> {
    return super.post<RenderResponse>('/api/documents/preview', { content });
  }
}

export const documentService = new DocumentService();
