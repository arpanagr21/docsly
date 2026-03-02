'use client';

import React, { useState } from 'react';
import { useComponents } from '@/hooks/useComponents';
import { Box, Search, Loader2, Check } from 'lucide-react';
import type { Component } from '@/types';

export interface ComponentPickerProps {
  selectedComponent?: string;
  onSelect: (component: Component) => void;
}

const CORE_COMPONENTS: Component[] = [
  {
    id: -1,
    user_id: null,
    name: 'row',
    version: '1',
    schema: {
      type: 'object',
      properties: {
        columns: { type: 'number', default: 2 },
        gap: { type: 'string', default: '1rem' },
        class: { type: 'string' },
        style: { type: 'string' },
      },
    },
    template: '',
    is_active: true,
    is_builtin: true,
  },
  {
    id: -2,
    user_id: null,
    name: 'column',
    version: '1',
    schema: {
      type: 'object',
      properties: {
        span: { type: 'number', default: 6 },
        class: { type: 'string' },
        style: { type: 'string' },
      },
    },
    template: '',
    is_active: true,
    is_builtin: true,
  },
  {
    id: -3,
    user_id: null,
    name: 'table',
    version: '1',
    schema: {
      type: 'object',
      properties: {
        headers: { type: 'array', default: ['Column A', 'Column B'] },
        rows: { type: 'array', default: [['Value 1', 'Value 2']] },
        class: { type: 'string' },
        style: { type: 'string' },
      },
    },
    template: '',
    is_active: true,
    is_builtin: true,
  },
];

export function ComponentPicker({ selectedComponent, onSelect }: ComponentPickerProps) {
  const { data: components, isLoading, error } = useComponents();
  const [searchQuery, setSearchQuery] = useState('');

  const mergedComponents = (() => {
    const byName = new Map<string, Component>();
    for (const component of CORE_COMPONENTS) {
      byName.set(component.name, component);
    }
    for (const component of components || []) {
      byName.set(component.name, component);
    }
    return Array.from(byName.values());
  })();

  const filteredComponents = mergedComponents.filter((component) =>
    component.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        <span className="ml-2 text-gray-500">Loading components...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-red-500 text-sm py-4">
        Failed to load components. Please try again.
      </div>
    );
  }

  if (!mergedComponents || mergedComponents.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <Box className="w-12 h-12 mx-auto mb-2 opacity-50" />
        <p>No components available.</p>
        <p className="text-sm">Create a component first to use it here.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search components..."
          className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 max-h-[240px] overflow-y-auto">
        {filteredComponents.map((component) => {
          const isSelected = selectedComponent === component.name;
          const propCount = Object.keys(component.schema?.properties || {}).length;

          return (
            <button
              key={component.id}
              onClick={() => onSelect(component)}
              className={`relative flex flex-col items-start p-3 rounded-lg border-2 transition-all text-left hover:shadow-md ${
                isSelected
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300 bg-white'
              }`}
            >
              {isSelected && (
                <div className="absolute top-2 right-2">
                  <Check className="w-4 h-4 text-blue-500" />
                </div>
              )}
              <div className="flex items-center gap-2 mb-1">
                <Box className={`w-4 h-4 ${isSelected ? 'text-blue-500' : 'text-gray-400'}`} />
                <span className={`font-medium text-sm ${isSelected ? 'text-blue-700' : 'text-gray-700'}`}>
                  {component.name}
                </span>
              </div>
              <div className="flex items-center gap-2 text-xs text-gray-500">
                <span>{propCount} {propCount === 1 ? 'prop' : 'props'}</span>
                {component.is_builtin && (
                  <span className="px-1.5 py-0.5 bg-gray-100 rounded text-gray-600">
                    built-in
                  </span>
                )}
              </div>
            </button>
          );
        })}
      </div>

      {filteredComponents.length === 0 && searchQuery && (
        <div className="text-center py-4 text-gray-500 text-sm">
          No components match "{searchQuery}"
        </div>
      )}
    </div>
  );
}
