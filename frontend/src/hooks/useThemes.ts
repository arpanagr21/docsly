'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { themeService } from '@/lib/api/services';
import type { ThemeCreateData, ThemeUpdateData } from '@/types';

export function useThemes() {
  return useQuery({
    queryKey: ['themes'],
    queryFn: () => themeService.list(),
    select: (data) => data.themes,
  });
}

export function useTheme(id: number) {
  return useQuery({
    queryKey: ['themes', id],
    queryFn: () => themeService.getById(id),
    select: (data) => data.theme,
    enabled: !!id,
  });
}

export function useCreateTheme() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ThemeCreateData) => themeService.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['themes'] });
    },
  });
}

export function useUpdateTheme() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: ThemeUpdateData }) =>
      themeService.update(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['themes'] });
      queryClient.invalidateQueries({ queryKey: ['themes', id] });
    },
  });
}

export function useDeleteTheme() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => themeService.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['themes'] });
    },
  });
}
