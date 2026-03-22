/**
 * Zod validation schemas matching backend Pydantic models.
 * FIX-028: Frontend input validation (byte-for-byte match with backend rules).
 */
import { z } from "zod";

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------

const passwordSchema = z
  .string()
  .min(8, "Password must be at least 8 characters")
  .max(100, "Password must be at most 100 characters")
  .refine((v) => /[A-Z]/.test(v), "Must contain an uppercase letter")
  .refine((v) => /[a-z]/.test(v), "Must contain a lowercase letter")
  .refine((v) => /\d/.test(v), "Must contain a digit")
  .refine(
    (v) => /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(v),
    "Must contain a special character",
  );

const emailSchema = z.string().email("Invalid email address");

const slugPattern = /^[a-z0-9-]+$/;

// ---------------------------------------------------------------------------
// Auth schemas
// ---------------------------------------------------------------------------

export const loginSchema = z.object({
  username: z.string().min(1, "Username is required").max(255),
  password: z.string().min(1, "Password is required").max(255),
});

export const resetPasswordSchema = z
  .object({
    newPassword: passwordSchema,
    confirmPassword: z.string(),
  })
  .refine((d) => d.newPassword === d.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

export const acceptInvitationSchema = z
  .object({
    username: z
      .string()
      .min(3, "Username must be at least 3 characters")
      .max(100, "Username must be at most 100 characters"),
    full_name: z
      .string()
      .min(1, "Full name is required")
      .max(255, "Full name must be at most 255 characters"),
    password: passwordSchema,
    confirmPassword: z.string(),
  })
  .refine((d) => d.password === d.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

// ---------------------------------------------------------------------------
// Document schemas
// ---------------------------------------------------------------------------

export const documentCreateSchema = z.object({
  title: z
    .string()
    .min(1, "Title is required")
    .max(500, "Title must be at most 500 characters"),
  description: z
    .string()
    .max(10000, "Description must be at most 10,000 characters")
    .optional()
    .or(z.literal("")),
  category: z
    .string()
    .max(100, "Category must be at most 100 characters")
    .optional()
    .or(z.literal("")),
  platform: z
    .string()
    .max(100, "Platform must be at most 100 characters")
    .optional()
    .or(z.literal("")),
  release_branch: z
    .string()
    .max(100, "Release branch must be at most 100 characters")
    .optional()
    .or(z.literal("")),
  tags: z
    .string()
    .max(2000, "Tags must be at most 2,000 characters")
    .optional()
    .or(z.literal("")),
});

export const documentUpdateSchema = z.object({
  title: z
    .string()
    .min(1, "Title is required")
    .max(500, "Title must be at most 500 characters")
    .optional(),
  description: z
    .string()
    .max(10000, "Description must be at most 10,000 characters")
    .optional()
    .or(z.literal("")),
  category: z
    .string()
    .max(100, "Category must be at most 100 characters")
    .optional()
    .or(z.literal("")),
  release_branch: z
    .string()
    .max(100, "Release branch must be at most 100 characters")
    .optional()
    .or(z.literal("")),
  reason: z
    .string()
    .min(3, "Reason must be at least 3 characters")
    .max(1000, "Reason must be at most 1,000 characters")
    .optional()
    .or(z.literal("")),
});

// ---------------------------------------------------------------------------
// Company schemas
// ---------------------------------------------------------------------------

export const companySchema = z.object({
  name: z
    .string()
    .min(2, "Name must be at least 2 characters")
    .max(100, "Name must be at most 100 characters"),
  slug: z
    .string()
    .min(2, "Slug must be at least 2 characters")
    .max(50, "Slug must be at most 50 characters")
    .regex(slugPattern, "Slug must contain only lowercase letters, numbers, and hyphens")
    .optional()
    .or(z.literal("")),
  contact_email: emailSchema.optional().or(z.literal("")),
  company_type: z.enum(["customer", "partner", "internal"]).default("customer"),
});

// ---------------------------------------------------------------------------
// Feedback schemas
// ---------------------------------------------------------------------------

export const feedbackSchema = z.object({
  feedback_type: z.enum(["question", "suggestion", "issue", "other"]),
  content: z
    .string()
    .min(10, "Feedback must be at least 10 characters")
    .max(5000, "Feedback must be at most 5,000 characters"),
});

export const feedbackResponseSchema = z.object({
  response: z
    .string()
    .min(1, "Response is required")
    .max(5000, "Response must be at most 5,000 characters"),
});

// ---------------------------------------------------------------------------
// Invitation schemas
// ---------------------------------------------------------------------------

export const invitationSchema = z.object({
  email: emailSchema,
  role: z.string().min(1, "Role is required"),
  message: z
    .string()
    .max(1000, "Message must be at most 1,000 characters")
    .optional()
    .or(z.literal("")),
});

// ---------------------------------------------------------------------------
// User schemas
// ---------------------------------------------------------------------------

export const userCreateSchema = z.object({
  username: z
    .string()
    .min(3, "Username must be at least 3 characters")
    .max(100, "Username must be at most 100 characters"),
  email: emailSchema,
  full_name: z
    .string()
    .min(1, "Full name is required")
    .max(255, "Full name must be at most 255 characters"),
  password: passwordSchema,
  role: z.string().min(1, "Role is required"),
});

export const userUpdateSchema = z.object({
  email: emailSchema.optional(),
  full_name: z
    .string()
    .min(1, "Full name is required")
    .max(255, "Full name must be at most 255 characters")
    .optional(),
  role: z.string().optional(),
});

export const profileUpdateSchema = z.object({
  full_name: z
    .string()
    .min(1, "Full name is required")
    .max(255, "Full name must be at most 255 characters"),
  timezone: z
    .string()
    .max(64, "Timezone must be at most 64 characters")
    .optional()
    .or(z.literal("")),
  locale: z
    .string()
    .max(10, "Locale must be at most 10 characters")
    .optional()
    .or(z.literal("")),
});

// ---------------------------------------------------------------------------
// Tenant provisioning
// ---------------------------------------------------------------------------

export const tenantProvisionSchema = z.object({
  tenant_name: z
    .string()
    .min(2, "Tenant name must be at least 2 characters")
    .max(255, "Tenant name must be at most 255 characters"),
  tenant_slug: z
    .string()
    .min(2, "Slug must be at least 2 characters")
    .max(100, "Slug must be at most 100 characters")
    .regex(slugPattern, "Slug must contain only lowercase letters, numbers, and hyphens"),
  admin_username: z
    .string()
    .min(3, "Username must be at least 3 characters")
    .max(50, "Username must be at most 50 characters"),
  admin_email: emailSchema,
  admin_password: passwordSchema,
  company_type: z.enum(["customer", "partner", "internal"]).default("customer"),
  contact_email: emailSchema.optional().or(z.literal("")),
});

// ---------------------------------------------------------------------------
// Canned responses
// ---------------------------------------------------------------------------

export const cannedResponseSchema = z.object({
  title: z
    .string()
    .min(1, "Title is required")
    .max(200, "Title must be at most 200 characters"),
  content: z
    .string()
    .min(1, "Content is required")
    .max(10000, "Content must be at most 10,000 characters"),
  category: z
    .string()
    .max(100, "Category must be at most 100 characters")
    .optional()
    .or(z.literal("")),
});

// ---------------------------------------------------------------------------
// Export types
// ---------------------------------------------------------------------------

export type LoginInput = z.infer<typeof loginSchema>;
export type ResetPasswordInput = z.infer<typeof resetPasswordSchema>;
export type AcceptInvitationInput = z.infer<typeof acceptInvitationSchema>;
export type DocumentCreateInput = z.infer<typeof documentCreateSchema>;
export type DocumentUpdateInput = z.infer<typeof documentUpdateSchema>;
export type CompanyInput = z.infer<typeof companySchema>;
export type FeedbackInput = z.infer<typeof feedbackSchema>;
export type FeedbackResponseInput = z.infer<typeof feedbackResponseSchema>;
export type InvitationInput = z.infer<typeof invitationSchema>;
export type UserCreateInput = z.infer<typeof userCreateSchema>;
export type UserUpdateInput = z.infer<typeof userUpdateSchema>;
export type ProfileUpdateInput = z.infer<typeof profileUpdateSchema>;
export type TenantProvisionInput = z.infer<typeof tenantProvisionSchema>;
export type CannedResponseInput = z.infer<typeof cannedResponseSchema>;
