/**
 * Shared filter validation, normalization, and matching utilities
 * Used by both Angular and Svelte generated components
 */

export type FieldType = 'date' | 'datetime' | 'number' | 'string';

/**
 * Validates a filter value based on field type
 * @param field - Field name
 * @param value - Filter value (may contain operators like >=, >, <=, <)
 * @param fieldTypes - Map of field names to their types
 * @returns true if valid, false otherwise
 */
export function isValidFilterValue(
  field: string,
  value: string,
  fieldTypes: Record<string, FieldType>
): boolean {
  const fieldType = fieldTypes[field];
  if (!fieldType) return true;

  // Extract operator and operand
  const match = value.match(/^(>=|>|<=|<)(.*)$/);
  const operand = match ? match[2].trim() : value;

  switch (fieldType) {
    case 'date':
      // Must match YYYY-MM-DD format
      return /^\d{4}-\d{2}-\d{2}$/.test(operand);
    case 'datetime':
      // Must match YYYY-MM-DD HH:MM or YYYY-MM-DDTHH:MM or with seconds, or just YYYY-MM-DD
      return /^\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2})?)?$/.test(operand);
    case 'number':
      // Must be a valid number
      return !isNaN(Number(operand)) && operand.trim() !== '';
    default:
      return true;
  }
}

/**
 * Normalizes a filter value for backend compatibility
 * @param field - Field name
 * @param value - Filter value
 * @param fieldTypes - Map of field names to their types
 * @returns Normalized value
 */
export function normalizeFilterValue(
  field: string,
  value: string,
  fieldTypes: Record<string, FieldType>
): string {
  const fieldType = fieldTypes[field];
  if (!fieldType) return value;

  const match = value.match(/^(>=|>|<=|<)(.*)$/);
  const operator = match ? match[1] : '';
  const operand = match ? match[2].trim() : value;

  if (fieldType === 'datetime') {
    // Replace 'T' with space for backend compatibility
    let normalized = operand.replace('T', ' ');
    // If only date is provided (YYYY-MM-DD), append 00:00
    if (/^\d{4}-\d{2}-\d{2}$/.test(normalized)) {
      normalized = normalized + ' 00:00';
    }
    return operator + normalized;
  }

  return value;
}

/**
 * Matches an item value against a filter value with operator support
 * @param itemValue - Value from the item to match
 * @param filterValue - Filter value (may contain operators)
 * @returns true if matches, false otherwise
 */
export function matchFilter(itemValue: unknown, filterValue: string): boolean {
  if (!filterValue) return true;

  // Detect comparison operator
  const match = filterValue.match(/^(>=|>|<=|<)(.*)$/);
  if (match) {
    const [, op, val] = match;
    const trimmedVal = val.trim();

    // Try numeric comparison first
    const numVal = Number(trimmedVal);
    const numItem = Number(itemValue);
    if (!isNaN(numVal) && !isNaN(numItem)) {
      if (op === '>=') return numItem >= numVal;
      if (op === '>') return numItem > numVal;
      if (op === '<=') return numItem <= numVal;
      if (op === '<') return numItem < numVal;
    }

    // Otherwise lexicographic comparison (for dates/strings)
    // Normalize datetime: replace 'T' with space for consistent comparison
    const strItem = String(itemValue ?? '').replace('T', ' ');
    const normalizedVal = trimmedVal.replace('T', ' ');
    if (op === '>=') return strItem >= normalizedVal;
    if (op === '>') return strItem > normalizedVal;
    if (op === '<=') return strItem <= normalizedVal;
    if (op === '<') return strItem < normalizedVal;
  }

  // Normal text filter (startsWith + unaccent)
  return removeAccents(String(itemValue ?? '').toLowerCase())
    .startsWith(removeAccents(filterValue.toLowerCase()));
}

/**
 * Removes accents from a string for case-insensitive comparison
 * @param s - String to normalize
 * @returns String without accents
 */
export function removeAccents(s: string): string {
  return s.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
}

/**
 * Formats a cell value for display
 * @param v - Value to format
 * @returns Formatted string
 */
export function fmtCell(v: unknown): string {
  if (v == null) return '';
  if (Array.isArray(v)) return `JSON [${v.length}]`;
  if (typeof v === 'object') return 'JSON {…}';
  const s = String(v);
  // Truncate UUIDs
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(s)
    ? s.slice(0, 8) + '…' : s;
}

/**
 * Gets the title (tooltip) for a cell
 * @param v - Value to display
 * @returns Title string
 */
export function cellTitle(v: unknown): string {
  if (v == null || typeof v === 'object') return '';
  return String(v);
}

/**
 * Parses URL query parameters to extract filter values
 * @param params - URLSearchParams or Record of query params
 * @param fieldTypes - Map of field names to their types
 * @returns Record of filter field names to values
 */
export function parseFiltersFromUrl(
  params: URLSearchParams | Record<string, string>,
  fieldTypes: Record<string, FieldType>
): Record<string, string> {
  const urlFilters: Record<string, string> = {};

  const entries = params instanceof URLSearchParams
    ? Array.from(params.entries())
    : Object.entries(params);

  entries.forEach(([key, value]) => {
    if (key.startsWith('f_') && typeof value === 'string') {
      const fieldName = key.substring(2);
      const decodedValue = decodeURIComponent(value);

      // Validate before accepting
      if (isValidFilterValue(fieldName, decodedValue, fieldTypes)) {
        urlFilters[fieldName] = decodedValue;
      }
    }
  });

  return urlFilters;
}

/**
 * Encodes filters into URL query parameter format
 * @param filters - Record of filter field names to values
 * @param fieldTypes - Map of field names to their types
 * @returns Record of URL parameter names (f_fieldname) to encoded values
 */
export function encodeFiltersToUrlParams(
  filters: Record<string, string>,
  fieldTypes: Record<string, FieldType>
): Record<string, string> {
  const params: Record<string, string> = {};

  Object.entries(filters).forEach(([field, value]) => {
    if (value && isValidFilterValue(field, value, fieldTypes)) {
      params[`f_${field}`] = encodeURIComponent(value);
    }
  });

  return params;
}
