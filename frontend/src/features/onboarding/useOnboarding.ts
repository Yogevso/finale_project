import { useMemo } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '@/lib/api'
import type { UserOnboardingState, UserRole } from '@/types'

import {
  getOnboardingConfig,
  ONBOARDING_CHECKLIST_VERSION,
  ONBOARDING_GUIDE_VERSION,
} from './config'

const ONBOARDING_QUERY_KEY = ['users', 'me', 'onboarding']

const DEFAULT_ONBOARDING_STATE: UserOnboardingState = {
  guide_version: ONBOARDING_GUIDE_VERSION,
  guide_seen_at: null,
  checklist_version: ONBOARDING_CHECKLIST_VERSION,
  completed_steps: [],
  checklist_completed_at: null,
}

export function useOnboarding(role: UserRole | undefined) {
  const queryClient = useQueryClient()
  const config = useMemo(() => (role ? getOnboardingConfig(role) : null), [role])

  const query = useQuery({
    queryKey: ONBOARDING_QUERY_KEY,
    queryFn: () => api.getMyOnboardingState(),
    enabled: Boolean(role),
  })

  const mutation = useMutation({
    mutationFn: api.updateMyOnboardingState.bind(api),
    onSuccess: (nextState) => {
      queryClient.setQueryData(ONBOARDING_QUERY_KEY, nextState)
    },
  })

  const serverState = query.data ?? DEFAULT_ONBOARDING_STATE
  const validStepIds = new Set(config?.steps.map((step) => step.id) ?? [])
  const completedSteps =
    serverState.checklist_version === ONBOARDING_CHECKLIST_VERSION
      ? serverState.completed_steps.filter((stepId) => validStepIds.has(stepId))
      : []
  const completedCount = completedSteps.length
  const totalSteps = config?.steps.length ?? 0
  const isChecklistComplete = totalSteps > 0 && completedCount === totalSteps
  const shouldAutoOpenGuide =
    Boolean(config) &&
    query.isSuccess &&
    (!serverState.guide_seen_at || serverState.guide_version !== ONBOARDING_GUIDE_VERSION)

  const markGuideSeen = async () => {
    if (!role) {
      return DEFAULT_ONBOARDING_STATE
    }
    return mutation.mutateAsync({
      guide_version: ONBOARDING_GUIDE_VERSION,
      guide_seen_at: new Date().toISOString(),
    })
  }

  const toggleChecklistStep = async (stepId: string) => {
    if (!validStepIds.has(stepId)) {
      return serverState
    }
    const nextCompletedSteps = completedSteps.includes(stepId)
      ? completedSteps.filter((currentStepId) => currentStepId !== stepId)
      : [...completedSteps, stepId]

    return mutation.mutateAsync({
      checklist_version: ONBOARDING_CHECKLIST_VERSION,
      completed_steps: nextCompletedSteps,
      checklist_completed_at:
        nextCompletedSteps.length === totalSteps && totalSteps > 0
          ? new Date().toISOString()
          : null,
    })
  }

  const resetChecklist = async () =>
    mutation.mutateAsync({
      checklist_version: ONBOARDING_CHECKLIST_VERSION,
      completed_steps: [],
      checklist_completed_at: null,
    })

  return {
    config,
    query,
    serverState,
    completedSteps,
    completedCount,
    totalSteps,
    isChecklistComplete,
    shouldAutoOpenGuide,
    isPending: mutation.isPending,
    markGuideSeen,
    toggleChecklistStep,
    resetChecklist,
  }
}
