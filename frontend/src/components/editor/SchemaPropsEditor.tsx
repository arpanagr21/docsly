'use client';

import React, { useState } from 'react';
import { Textarea } from '@/components/ui/textarea';
import { ChevronDown, ChevronRight, Plus, Trash2 } from 'lucide-react';
import type { JSONSchema } from '@/types';

export interface SchemaPropsEditorProps {
  schema: JSONSchema;
  props: Record<string, unknown>;
  onChange: (props: Record<string, unknown>) => void;
}

interface SchemaProperty {
  type: string;
  description?: string;
  default?: unknown;
  enum?: string[];
  items?: SchemaProperty & { properties?: Record<string, SchemaProperty> };
  properties?: Record<string, SchemaProperty>;
  required?: string[];
  minLength?: number;
  maxLength?: number;
  minimum?: number;
  maximum?: number;
}

// Sub-component for rendering nested object properties
function ObjectFieldEditor({
  property,
  value,
  onChange,
  label,
  isRequired,
}: {
  property: SchemaProperty;
  value: Record<string, unknown>;
  onChange: (value: Record<string, unknown>) => void;
  label: string;
  isRequired: boolean;
}) {
  const [isExpanded, setIsExpanded] = useState(true);
  const properties = property.properties || {};
  const requiredFields = property.required || [];

  const handleFieldChange = (key: string, fieldValue: unknown) => {
    onChange({
      ...value,
      [key]: fieldValue,
    });
  };

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-3 py-2 bg-gray-50 hover:bg-gray-100 transition-colors"
      >
        <span className="text-sm font-medium text-gray-700">
          {label}
          {isRequired && <span className="text-red-500 ml-1">*</span>}
        </span>
        {isExpanded ? (
          <ChevronDown className="w-4 h-4 text-gray-500" />
        ) : (
          <ChevronRight className="w-4 h-4 text-gray-500" />
        )}
      </button>
      {isExpanded && (
        <div className="p-3 space-y-3 bg-white">
          {property.description && (
            <p className="text-xs text-gray-500">{property.description}</p>
          )}
          {Object.entries(properties).map(([key, prop]) => (
            <FieldRenderer
              key={key}
              fieldKey={key}
              property={prop as SchemaProperty}
              value={value[key]}
              onChange={(v) => handleFieldChange(key, v)}
              isRequired={requiredFields.includes(key)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// Sub-component for rendering arrays of objects
function ArrayOfObjectsEditor({
  property,
  value,
  onChange,
  label,
  isRequired,
}: {
  property: SchemaProperty;
  value: Record<string, unknown>[];
  onChange: (value: Record<string, unknown>[]) => void;
  label: string;
  isRequired: boolean;
}) {
  const itemProperties = (property.items as SchemaProperty)?.properties || {};
  const itemRequired = (property.items as SchemaProperty)?.required || [];

  const createEmptyItem = (): Record<string, unknown> => {
    const item: Record<string, unknown> = {};
    for (const [key, prop] of Object.entries(itemProperties)) {
      const p = prop as SchemaProperty;
      if (p.default !== undefined) {
        item[key] = p.default;
      } else if (p.type === 'string') {
        item[key] = '';
      } else if (p.type === 'number' || p.type === 'integer') {
        item[key] = 0;
      } else if (p.type === 'boolean') {
        item[key] = false;
      } else if (p.type === 'array') {
        item[key] = [];
      } else if (p.type === 'object') {
        item[key] = {};
      }
    }
    return item;
  };

  const handleItemChange = (index: number, itemValue: Record<string, unknown>) => {
    const newArray = [...value];
    newArray[index] = itemValue;
    onChange(newArray);
  };

  const handleAddItem = () => {
    onChange([...value, createEmptyItem()]);
  };

  const handleRemoveItem = (index: number) => {
    onChange(value.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-gray-700">
        {label}
        {isRequired && <span className="text-red-500 ml-1">*</span>}
      </label>
      {property.description && (
        <p className="text-xs text-gray-500">{property.description}</p>
      )}
      <div className="space-y-3">
        {value.map((item, index) => (
          <ArrayItemEditor
            key={index}
            index={index}
            itemProperties={itemProperties}
            itemRequired={itemRequired}
            item={item}
            onItemChange={(v) => handleItemChange(index, v)}
            onRemove={() => handleRemoveItem(index)}
          />
        ))}
        <button
          type="button"
          onClick={handleAddItem}
          className="w-full py-2 border-2 border-dashed border-gray-300 rounded-md text-sm text-gray-500 hover:border-blue-400 hover:text-blue-600 transition-colors flex items-center justify-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Add {label.replace(/s$/, '')}
        </button>
      </div>
    </div>
  );
}

// Editor for individual array items
function ArrayItemEditor({
  index,
  itemProperties,
  itemRequired,
  item,
  onItemChange,
  onRemove,
}: {
  index: number;
  itemProperties: Record<string, SchemaProperty>;
  itemRequired: string[];
  item: Record<string, unknown>;
  onItemChange: (value: Record<string, unknown>) => void;
  onRemove: () => void;
}) {
  const [isExpanded, setIsExpanded] = useState(true);

  const handleFieldChange = (key: string, value: unknown) => {
    onItemChange({
      ...item,
      [key]: value,
    });
  };

  // Get a preview of the item for the header
  const itemPreview = Object.values(item).find((v) => typeof v === 'string' && v.length > 0) || `Item ${index + 1}`;

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden bg-white">
      <div className="flex items-center justify-between px-3 py-2 bg-gray-50">
        <button
          type="button"
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-2 text-sm font-medium text-gray-700 hover:text-gray-900"
        >
          {isExpanded ? (
            <ChevronDown className="w-4 h-4 text-gray-500" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-500" />
          )}
          <span className="truncate max-w-[200px]">{String(itemPreview)}</span>
        </button>
        <button
          type="button"
          onClick={onRemove}
          className="p-1 text-red-500 hover:text-red-700 hover:bg-red-50 rounded"
          title="Remove item"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
      {isExpanded && (
        <div className="p-3 space-y-3 border-t border-gray-100">
          {Object.entries(itemProperties).map(([key, prop]) => (
            <FieldRenderer
              key={key}
              fieldKey={key}
              property={prop as SchemaProperty}
              value={item[key]}
              onChange={(v) => handleFieldChange(key, v)}
              isRequired={itemRequired.includes(key)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// Main field renderer that handles all types
function FieldRenderer({
  fieldKey,
  property,
  value,
  onChange,
  isRequired,
}: {
  fieldKey: string;
  property: SchemaProperty;
  value: unknown;
  onChange: (value: unknown) => void;
  isRequired: boolean;
}) {
  const label = fieldKey.charAt(0).toUpperCase() + fieldKey.slice(1).replace(/_/g, ' ');

  // Handle enum type (dropdown)
  if (property.enum && property.enum.length > 0) {
    return (
      <div className="space-y-1">
        <label className="block text-sm font-medium text-gray-700">
          {label}
          {isRequired && <span className="text-red-500 ml-1">*</span>}
        </label>
        {property.description && (
          <p className="text-xs text-gray-500">{property.description}</p>
        )}
        <select
          value={String(value || '')}
          onChange={(e) => onChange(e.target.value)}
          className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Select {label.toLowerCase()}...</option>
          {property.enum.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </div>
    );
  }

  // Handle different types
  switch (property.type) {
    case 'string': {
      const isLongText =
        (property.maxLength && property.maxLength > 100) ||
        fieldKey.toLowerCase().includes('description') ||
        fieldKey.toLowerCase().includes('content') ||
        fieldKey.toLowerCase().includes('text');

      if (isLongText) {
        return (
          <div className="space-y-1">
            <label className="block text-sm font-medium text-gray-700">
              {label}
              {isRequired && <span className="text-red-500 ml-1">*</span>}
            </label>
            {property.description && (
              <p className="text-xs text-gray-500">{property.description}</p>
            )}
            <Textarea
              value={String(value || '')}
              onChange={(e) => onChange(e.target.value)}
              placeholder={property.description || `Enter ${label.toLowerCase()}...`}
              className="min-h-[80px] text-sm"
            />
          </div>
        );
      }

      return (
        <div className="space-y-1">
          <label className="block text-sm font-medium text-gray-700">
            {label}
            {isRequired && <span className="text-red-500 ml-1">*</span>}
          </label>
          {property.description && (
            <p className="text-xs text-gray-500">{property.description}</p>
          )}
          <input
            type="text"
            value={String(value || '')}
            onChange={(e) => onChange(e.target.value)}
            placeholder={property.description || `Enter ${label.toLowerCase()}...`}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      );
    }

    case 'number':
    case 'integer':
      return (
        <div className="space-y-1">
          <label className="block text-sm font-medium text-gray-700">
            {label}
            {isRequired && <span className="text-red-500 ml-1">*</span>}
          </label>
          {property.description && (
            <p className="text-xs text-gray-500">{property.description}</p>
          )}
          <input
            type="number"
            value={value !== undefined && value !== null ? Number(value) : ''}
            onChange={(e) => onChange(e.target.value ? Number(e.target.value) : undefined)}
            min={property.minimum}
            max={property.maximum}
            placeholder={property.description || `Enter ${label.toLowerCase()}...`}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      );

    case 'boolean':
      return (
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={Boolean(value)}
                onChange={(e) => onChange(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-500 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
            <span className="text-sm font-medium text-gray-700">
              {label}
              {isRequired && <span className="text-red-500 ml-1">*</span>}
            </span>
          </div>
          {property.description && (
            <p className="text-xs text-gray-500 ml-12">{property.description}</p>
          )}
        </div>
      );

    case 'array': {
      const arrayValue = Array.isArray(value) ? value : [];
      const itemType = property.items?.type || 'string';

      // Check if array items are objects
      if (itemType === 'object' && property.items?.properties) {
        return (
          <ArrayOfObjectsEditor
            property={property}
            value={arrayValue as Record<string, unknown>[]}
            onChange={onChange as (value: Record<string, unknown>[]) => void}
            label={label}
            isRequired={isRequired}
          />
        );
      }

      // Simple array (strings or numbers)
      return (
        <div className="space-y-1">
          <label className="block text-sm font-medium text-gray-700">
            {label}
            {isRequired && <span className="text-red-500 ml-1">*</span>}
          </label>
          {property.description && (
            <p className="text-xs text-gray-500">{property.description}</p>
          )}
          <div className="space-y-2">
            {arrayValue.map((item, index) => (
              <div key={index} className="flex items-center gap-2">
                <input
                  type={itemType === 'number' ? 'number' : 'text'}
                  value={String(item || '')}
                  onChange={(e) => {
                    const newArray = [...arrayValue];
                    newArray[index] = itemType === 'number' ? Number(e.target.value) : e.target.value;
                    onChange(newArray);
                  }}
                  placeholder={`Item ${index + 1}`}
                  className="flex-1 border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <button
                  type="button"
                  onClick={() => {
                    const newArray = arrayValue.filter((_, i) => i !== index);
                    onChange(newArray);
                  }}
                  className="p-2 text-red-500 hover:text-red-700 hover:bg-red-50 rounded"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
            <button
              type="button"
              onClick={() => onChange([...arrayValue, itemType === 'number' ? 0 : ''])}
              className="w-full py-2 border-2 border-dashed border-gray-300 rounded-md text-sm text-gray-500 hover:border-blue-400 hover:text-blue-600 transition-colors flex items-center justify-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Add item
            </button>
          </div>
        </div>
      );
    }

    case 'object': {
      if (property.properties) {
        return (
          <ObjectFieldEditor
            property={property}
            value={(value as Record<string, unknown>) || {}}
            onChange={onChange as (value: Record<string, unknown>) => void}
            label={label}
            isRequired={isRequired}
          />
        );
      }
      // Fallback for objects without defined properties
      return (
        <div className="space-y-1">
          <label className="block text-sm font-medium text-gray-700">
            {label}
            {isRequired && <span className="text-red-500 ml-1">*</span>}
          </label>
          {property.description && (
            <p className="text-xs text-gray-500">{property.description}</p>
          )}
          <Textarea
            value={typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value || '{}')}
            onChange={(e) => {
              try {
                onChange(JSON.parse(e.target.value));
              } catch {
                // Invalid JSON, keep current value
              }
            }}
            placeholder="Enter JSON object..."
            className="min-h-[80px] text-sm font-mono"
          />
        </div>
      );
    }

    default:
      // Fallback to text input for unknown types
      return (
        <div className="space-y-1">
          <label className="block text-sm font-medium text-gray-700">
            {label}
            {isRequired && <span className="text-red-500 ml-1">*</span>}
          </label>
          {property.description && (
            <p className="text-xs text-gray-500">{property.description}</p>
          )}
          <input
            type="text"
            value={String(value || '')}
            onChange={(e) => onChange(e.target.value)}
            placeholder={`Enter ${label.toLowerCase()}...`}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      );
  }
}

export function SchemaPropsEditor({ schema, props, onChange }: SchemaPropsEditorProps) {
  const properties = schema?.properties || {};
  const requiredFields = schema?.required || [];

  const handleChange = (key: string, value: unknown) => {
    onChange({
      ...props,
      [key]: value,
    });
  };

  const propertyEntries = Object.entries(properties);

  if (propertyEntries.length === 0) {
    return (
      <div className="text-center py-4 text-gray-500 text-sm">
        This component has no configurable properties.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {propertyEntries.map(([key, property]) => (
        <FieldRenderer
          key={key}
          fieldKey={key}
          property={property as SchemaProperty}
          value={props[key]}
          onChange={(v) => handleChange(key, v)}
          isRequired={requiredFields.includes(key)}
        />
      ))}
    </div>
  );
}
