'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { componentService } from '@/lib/api/services';
import type { ComponentCreateData, ComponentUpdateData } from '@/types';

export function useComponents() {
  return useQuery({
    queryKey: ['components'],
    queryFn: () => componentService.list(),
    select: (data) => data.components,
  });
}

export function useComponent(id: number) {
  return useQuery({
    queryKey: ['components', id],
    queryFn: () => componentService.getById(id),
    select: (data) => data.component,
    enabled: !!id,
  });
}

export function useComponentByName(name: string) {
  return useQuery({
    queryKey: ['components', 'name', name],
    queryFn: () => componentService.getByName(name),
    select: (data) => data.component,
    enabled: !!name,
  });
}

export function useCreateComponent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ComponentCreateData) => componentService.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['components'] });
    },
  });
}

export function useUpdateComponent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: ComponentUpdateData }) =>
      componentService.update(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['components'] });
      queryClient.invalidateQueries({ queryKey: ['components', id] });
    },
  });
}

export function useDeleteComponent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => componentService.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['components'] });
    },
  });
}
