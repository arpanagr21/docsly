'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { documentService } from '@/lib/api/documents';
import type { CreateDocumentData, UpdateDocumentData } from '@/types/document';

export function useDocuments() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['documents'],
    queryFn: () => documentService.list(),
  });

  return {
    documents: data?.documents ?? [],
    isLoading,
    error,
    refetch,
  };
}

export function useDocument(id: number) {
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ['document', id],
    queryFn: () => documentService.getById(id),
    enabled: !!id,
  });

  const updateMutation = useMutation({
    mutationFn: (data: UpdateDocumentData) => documentService.update(id, data),
    onSuccess: (result) => {
      queryClient.setQueryData(['document', id], result);
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => documentService.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      queryClient.removeQueries({ queryKey: ['document', id] });
    },
  });

  const save = async (data: UpdateDocumentData) => {
    return updateMutation.mutateAsync(data);
  };

  const deleteDocument = async () => {
    return deleteMutation.mutateAsync();
  };

  return {
    document: data?.document,
    isLoading,
    error,
    save,
    isSaving: updateMutation.isPending,
    delete: deleteDocument,
    isDeleting: deleteMutation.isPending,
  };
}

export function useCreateDocument() {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (data: CreateDocumentData) => documentService.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });

  return {
    create: mutation.mutateAsync,
    isCreating: mutation.isPending,
    error: mutation.error,
  };
}

export function useDocumentPreview(id: number) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['document-preview', id],
    queryFn: () => documentService.render(id),
    enabled: !!id,
  });

  return {
    html: data?.html,
    isLoading,
    error,
    refetch,
  };
}
