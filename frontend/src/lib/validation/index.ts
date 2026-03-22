/**
 * Validation helpers for use in form components.
 */
import type { ZodSchema, ZodError } from "zod";

export type FieldErrors = Record<string, string>;

/**
 * Validate data against a Zod schema.
 * Returns `null` if valid, or a `FieldErrors` map of first error per field.
 */
export function validateForm<T>(
  schema: ZodSchema<T>,
  data: unknown,
): { data: T; errors: null } | { data: null; errors: FieldErrors } {
  const result = schema.safeParse(data);
  if (result.success) {
    return { data: result.data, errors: null };
  }
  return { data: null, errors: formatZodErrors(result.error) };
}

/**
 * Format a ZodError into a flat field→message map (first error per path).
 */
export function formatZodErrors(error: ZodError): FieldErrors {
  const errors: FieldErrors = {};
  for (const issue of error.issues) {
    const key = issue.path.join(".");
    if (key && !errors[key]) {
      errors[key] = issue.message;
    }
  }
  return errors;
}
