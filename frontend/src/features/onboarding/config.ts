import type { UserRole } from '@/types'

export const ONBOARDING_GUIDE_VERSION = 1
export const ONBOARDING_CHECKLIST_VERSION = 1

export type OnboardingGuideCard = {
  title: string
  description: string
}

export type OnboardingStep = {
  id: string
  title: string
  description: string
  href: string
  hrefLabel: string
}

export type RoleOnboardingConfig = {
  title: string
  description: string
  primaryActionHref: string
  primaryActionLabel: string
  guideCards: OnboardingGuideCard[]
  checklistTitle: string
  checklistDescription: string
  steps: OnboardingStep[]
}

export function getOnboardingConfig(role: UserRole): RoleOnboardingConfig {
  switch (role) {
    case 'customer':
      return {
        title: 'Welcome to your customer portal',
        description:
          'Your portal keeps documents, support replies, chat, and feedback in one place so your team always sees the latest answer.',
        primaryActionHref: '/portal/documents',
        primaryActionLabel: 'Browse my documents',
        guideCards: [
          {
            title: 'Published docs only',
            description:
              'You only see documents that are published and assigned to your company.',
          },
          {
            title: 'Responses stay in-thread',
            description:
              'Support tickets and feedback now continue as real conversations instead of disconnected replies.',
          },
          {
            title: 'Work from one dashboard',
            description:
              'Use the dashboard to jump back into reading, support, and document updates quickly.',
          },
        ],
        checklistTitle: 'Customer onboarding checklist',
        checklistDescription:
          'Use this once to get familiar with the portal. You can reopen the guide or reset the checklist later.',
        steps: [
          {
            id: 'open_customer_documents',
            title: 'Open your document library',
            description: 'Review the documents your company can currently access.',
            href: '/portal/documents',
            hrefLabel: 'Open documents',
          },
          {
            id: 'open_customer_chat',
            title: 'Check your message center',
            description: 'Open customer chat so you know where direct conversations appear.',
            href: '/portal/chat',
            hrefLabel: 'Open messages',
          },
          {
            id: 'open_customer_support',
            title: 'Review support threads',
            description: 'Confirm where ticket updates and replies from the internal team appear.',
            href: '/portal/support',
            hrefLabel: 'Open support',
          },
          {
            id: 'open_customer_feedback',
            title: 'Review feedback history',
            description: 'See where your document feedback lives after it becomes a tracked thread.',
            href: '/portal/feedback',
            hrefLabel: 'Open feedback',
          },
        ],
      }
    case 'viewer':
      return {
        title: 'Welcome to the documentation workspace',
        description:
          'As a viewer, your job is to find trusted information quickly, follow updates, and keep your notification settings aligned with the content you care about.',
        primaryActionHref: '/documents',
        primaryActionLabel: 'Open documents',
        guideCards: [
          {
            title: 'Find content fast',
            description:
              'The documents page now has better filtering, sticky search, and clearer empty states.',
          },
          {
            title: 'Use guided tours',
            description:
              'The documents list and detail screens still have replayable in-product tours when you need them.',
          },
          {
            title: 'Track what matters',
            description:
              'Bookmarks, watches, and notification settings help you stay on top of important changes.',
          },
        ],
        checklistTitle: 'Viewer onboarding checklist',
        checklistDescription:
          'Complete these steps once so you know where to browse, follow, and manage your personal settings.',
        steps: [
          {
            id: 'open_internal_documents',
            title: 'Browse the documents workspace',
            description: 'Open the main documents page and review the search and filter layout.',
            href: '/documents',
            hrefLabel: 'Go to documents',
          },
          {
            id: 'open_first_document',
            title: 'Open a document detail view',
            description: 'Open any document to see preview, versions, attachments, and the detail tabs.',
            href: '/documents',
            hrefLabel: 'Find a document',
          },
          {
            id: 'review_notifications',
            title: 'Review notification preferences',
            description: 'Decide which updates should notify you by email.',
            href: '/profile#notifications',
            hrefLabel: 'Open notifications',
          },
        ],
      }
    case 'editor':
      return {
        title: 'Welcome to the editor workflow',
        description:
          'Your first job is to learn the content flow: create or upload, set the right audience, then submit for review without losing the original source file.',
        primaryActionHref: '/documents?action=create',
        primaryActionLabel: 'Create a document',
        guideCards: [
          {
            title: 'Draft or upload',
            description:
              'You can start with a blank document or upload source files up to 50 MB.',
          },
          {
            title: 'Audience matters',
            description:
              'Company visibility only works correctly after the audience assignments are set in the Details tab.',
          },
          {
            title: 'Reviews are part of the flow',
            description:
              'Submission, approval, and publish states now notify the right internal users again.',
          },
        ],
        checklistTitle: 'Editor onboarding checklist',
        checklistDescription:
          'Walk through the main authoring flow once so your first real document is faster and less error-prone.',
        steps: [
          {
            id: 'create_editor_document',
            title: 'Create a draft',
            description: 'Open the create flow and review the document fields and quick-start actions.',
            href: '/documents?action=create',
            hrefLabel: 'Create draft',
          },
          {
            id: 'upload_editor_document',
            title: 'Review the upload flow',
            description:
              'Check the upload modal so you know the size limit and PDF conversion options.',
            href: '/documents?action=upload',
            hrefLabel: 'Open upload',
          },
          {
            id: 'review_editor_details',
            title: 'Learn the details tab',
            description:
              'Open a document detail page and review company assignment, status, and audience controls.',
            href: '/documents',
            hrefLabel: 'Open documents',
          },
          {
            id: 'review_editor_queue',
            title: 'Review the approvals queue',
            description: 'See where review submission and approval work happens after editing.',
            href: '/reviews',
            hrefLabel: 'Open reviews',
          },
        ],
      }
    case 'manager':
      return {
        title: 'Welcome to the manager control flow',
        description:
          'Managers coordinate people, reviews, support, and visibility. The quickest win is learning where each queue now lives and how they connect.',
        primaryActionHref: '/users',
        primaryActionLabel: 'Open user management',
        guideCards: [
          {
            title: 'People and invitations',
            description:
              'Invitations now show delivery status and preview data so you can see what was sent.',
          },
          {
            title: 'Reviews and support',
            description:
              'Review, feedback, and support flows now notify the right people and link into conversations.',
          },
          {
            title: 'Document visibility',
            description:
              'Audience updates now refresh correctly across internal, customer, and viewer surfaces.',
          },
        ],
        checklistTitle: 'Manager onboarding checklist',
        checklistDescription:
          'Use this checklist to cover the queues and controls you are expected to manage.',
        steps: [
          {
            id: 'open_manager_users',
            title: 'Open users and invitations',
            description: 'Review user management, pending invitations, and delivery statuses.',
            href: '/users',
            hrefLabel: 'Open users',
          },
          {
            id: 'open_manager_reviews',
            title: 'Review the approvals queue',
            description: 'Open the review workspace so you know where pending approvals land.',
            href: '/reviews',
            hrefLabel: 'Open reviews',
          },
          {
            id: 'open_manager_support',
            title: 'Review support conversations',
            description: 'Check where ticket and feedback conversations now live.',
            href: '/support',
            hrefLabel: 'Open support',
          },
          {
            id: 'open_manager_documents',
            title: 'Inspect the documents workspace',
            description: 'Review filters, deleted-doc recovery, and company assignment behaviors.',
            href: '/documents',
            hrefLabel: 'Open documents',
          },
        ],
      }
    case 'admin':
      return {
        title: 'Welcome to the admin workspace',
        description:
          'Admins manage the operational side of the platform: people, companies, reviews, and document recovery.',
        primaryActionHref: '/users',
        primaryActionLabel: 'Open users',
        guideCards: [
          {
            title: 'User lifecycle is safer',
            description:
              'Admins can deactivate users, while permanent deletion remains reserved for SYSADMIN.',
          },
          {
            title: 'Company data now syncs',
            description:
              'Company-scoped document visibility and customer portal views now refresh more reliably.',
          },
          {
            title: 'Recovery is built in',
            description:
              'Deleted documents now use a 30-day recovery window instead of disappearing immediately.',
          },
        ],
        checklistTitle: 'Admin onboarding checklist',
        checklistDescription:
          'Cover the main admin surfaces once so you know where people, companies, and document recovery live.',
        steps: [
          {
            id: 'open_admin_users',
            title: 'Review users and invitations',
            description: 'Confirm where onboarding, invitations, and user lifecycle actions live.',
            href: '/users',
            hrefLabel: 'Open users',
          },
          {
            id: 'open_admin_companies',
            title: 'Review company management',
            description: 'Open companies so you know where customer entities are managed.',
            href: '/admin/companies',
            hrefLabel: 'Open companies',
          },
          {
            id: 'open_admin_documents',
            title: 'Review documents and recovery',
            description: 'Inspect the deleted-document recovery view and audience controls.',
            href: '/documents',
            hrefLabel: 'Open documents',
          },
          {
            id: 'open_admin_reviews',
            title: 'Check the review queue',
            description: 'Review how pending approvals are handled operationally.',
            href: '/reviews',
            hrefLabel: 'Open reviews',
          },
        ],
      }
    case 'system_admin':
      return {
        title: 'Welcome to the SYSADMIN control plane',
        description:
          'SYSADMIN owns the platform-level settings. The main onboarding goal is understanding where sender settings, lifecycle controls, and operational health live.',
        primaryActionHref: '/admin/system-setup',
        primaryActionLabel: 'Open system setup',
        guideCards: [
          {
            title: 'Control outbound email',
            description:
              'System setup now shows the active sender and lets you store new SMTP credentials in-app.',
          },
          {
            title: 'Control document lifecycle',
            description:
              'Auto-archive and recovery behavior are now configurable from system setup.',
          },
          {
            title: 'Watch platform health',
            description:
              'Admin Ops now reports collab health correctly so you can verify the stack quickly.',
          },
        ],
        checklistTitle: 'SYSADMIN onboarding checklist',
        checklistDescription:
          'Walk through the platform-level controls once so you know where to manage the system safely.',
        steps: [
          {
            id: 'open_sysadmin_setup',
            title: 'Review system setup',
            description: 'Inspect email sender and document lifecycle settings.',
            href: '/admin/system-setup',
            hrefLabel: 'Open system setup',
          },
          {
            id: 'open_sysadmin_users',
            title: 'Review users and invitations',
            description: 'Confirm where invitation status and permanent user deletion live.',
            href: '/users',
            hrefLabel: 'Open users',
          },
          {
            id: 'open_sysadmin_ops',
            title: 'Review admin operations',
            description: 'Open operational health and confirm the collab service status view.',
            href: '/admin/operations',
            hrefLabel: 'Open admin ops',
          },
          {
            id: 'open_sysadmin_documents',
            title: 'Review document recovery',
            description: 'Inspect archive, delete recovery, and document management behavior.',
            href: '/documents',
            hrefLabel: 'Open documents',
          },
        ],
      }
    default:
      return {
        title: 'Welcome aboard',
        description:
          'This quick guide helps you understand where documents, messages, and settings live before you start working.',
        primaryActionHref: '/dashboard',
        primaryActionLabel: 'Open dashboard',
        guideCards: [
          {
            title: 'Learn the workspace',
            description: 'Your dashboard, documents, and communication tools are linked together.',
          },
          {
            title: 'Use role-based views',
            description: 'What you see depends on your role and company assignment.',
          },
          {
            title: 'Replay later',
            description: 'You can always reopen onboarding and product tours if you need a refresher.',
          },
        ],
        checklistTitle: 'Welcome checklist',
        checklistDescription:
          'Use these steps to get comfortable with the platform before you start real work.',
        steps: [
          {
            id: 'open_dashboard',
            title: 'Review your dashboard',
            description: 'Start by checking the dashboard summary and recent activity.',
            href: '/dashboard',
            hrefLabel: 'Open dashboard',
          },
        ],
      }
  }
}
