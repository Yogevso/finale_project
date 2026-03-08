import { useCallback, useEffect, useMemo, useState } from 'react'
import type { CallBackProps, Step } from 'react-joyride'

type UseTourResult = {
  run: boolean
  onJoyrideCallback: (data: CallBackProps) => void
  completionStorageKey: string
}

export function useTour(tourKey: string, steps: Step[]): UseTourResult {
  const completionStorageKey = useMemo(() => `tour-completed-${tourKey}`, [tourKey])
  const [run, setRun] = useState(false)

  useEffect(() => {
    if (steps.length === 0) {
      setRun(false)
      return
    }
    const completed = window.localStorage.getItem(completionStorageKey) === '1'
    setRun(!completed)
  }, [completionStorageKey, steps.length])

  const onJoyrideCallback = useCallback(
    (data: CallBackProps) => {
      if (data.status === 'finished' || data.status === 'skipped') {
        window.localStorage.setItem(completionStorageKey, '1')
        setRun(false)
      }
    },
    [completionStorageKey],
  )

  return {
    run,
    onJoyrideCallback,
    completionStorageKey,
  }
}
