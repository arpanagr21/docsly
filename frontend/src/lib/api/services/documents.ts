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

  async downloadPdf(id: number, title?: string): Promise<void> {
    const token = this.getAccessToken();
    const response = await fetch(`${this.baseUrl}/api/documents/${id}/pdf`, {
      method: 'GET',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Failed to download PDF' }));
      throw new Error(error.error || 'Failed to download PDF');
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `${(title || 'document').replace(/[\\/]/g, '-')}.pdf`;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
  }

  async downloadPreviewPdf(content: DocumentContent, title?: string): Promise<void> {
    const token = this.getAccessToken();
    const response = await fetch(`${this.baseUrl}/api/documents/preview-pdf`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ content, title }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Failed to generate PDF' }));
      throw new Error(error.error || 'Failed to generate PDF');
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `${(title || 'document').replace(/[\\/]/g, '-')}.pdf`;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
  }
}

export const documentService = new DocumentService();
