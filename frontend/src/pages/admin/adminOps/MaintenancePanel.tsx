import { useCallback, useEffect, useState } from 'react'
import { Clock, Play, Plus, Square } from 'lucide-react'
import { api } from '@/lib/api'
import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import { FormField, SubmitButton, TextArea } from '@/components/form'
import { ListSkeleton } from '@/components/skeletons'
import { extractApiErrorMessage } from '@/lib/toast'
import type { MaintenanceWindow } from '@/lib/api/adminOpsApi'
import { toast } from 'sonner'

const emptyForm = {
  title: '',
  description: '',
  scheduled_start: '',
  scheduled_end: '',
  is_read_only: true,
}

type MaintenanceFormErrors = {
  title?: string
  scheduled_start?: string
  scheduled_end?: string
}

export default function MaintenancePanel() {
  const [windows, setWindows] = useState<MaintenanceWindow[]>([])
  const [loading, setLoading] = useState(true)
  const [hasError, setHasError] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState(emptyForm)
  const [formErrors, setFormErrors] = useState<MaintenanceFormErrors>({})
  const [isCreating, setIsCreating] = useState(false)

  const load = useCallback(() => {
    setHasError(false)
    setLoading(true)
    api.listMaintenanceWindows()
      .then(setWindows)
      .catch(() => setHasError(true))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const clearFormError = (field: keyof MaintenanceFormErrors) => {
    if (!formErrors[field]) {
      return
    }

    setFormErrors((current) => ({
      ...current,
      [field]: undefined,
    }))
  }

  const handleCreate = async () => {
    const nextErrors: MaintenanceFormErrors = {}
    const trimmedTitle = form.title.trim()
    const startDate = form.scheduled_start ? new Date(form.scheduled_start) : null
    const endDate = form.scheduled_end ? new Date(form.scheduled_end) : null

    if (!trimmedTitle) {
      nextErrors.title = 'Title is required.'
    }

    if (!form.scheduled_start) {
      nextErrors.scheduled_start = 'Start date and time are required.'
    } else if (Number.isNaN(startDate?.getTime())) {
      nextErrors.scheduled_start = 'Enter a valid start date and time.'
    }

    if (!form.scheduled_end) {
      nextErrors.scheduled_end = 'End date and time are required.'
    } else if (Number.isNaN(endDate?.getTime())) {
      nextErrors.scheduled_end = 'Enter a valid end date and time.'
    }

    if (
      !nextErrors.scheduled_start &&
      !nextErrors.scheduled_end &&
      startDate &&
      endDate &&
      endDate <= startDate
    ) {
      nextErrors.scheduled_end = 'End date and time must be after the start.'
    }

    if (Object.values(nextErrors).some(Boolean)) {
      setFormErrors(nextErrors)
      return
    }

    setFormErrors({})
    setIsCreating(true)
    try {
      await api.createMaintenanceWindow({
        title: trimmedTitle,
        description: form.description.trim() || undefined,
        scheduled_start: startDate!.toISOString(),
        scheduled_end: endDate!.toISOString(),
        is_read_only: form.is_read_only,
      })
      toast.success('Maintenance window created')
      setShowCreate(false)
      setForm(emptyForm)
      setFormErrors({})
      load()
    } catch (error: unknown) {
      toast.error(extractApiErrorMessage(error, 'Creation failed'))
    } finally {
      setIsCreating(false)
    }
  }

  const handleToggle = async (windowItem: MaintenanceWindow) => {
    try {
      if (windowItem.is_active) {
        await api.deactivateMaintenanceWindow(windowItem.id)
        toast.success('Maintenance deactivated')
      } else {
        await api.activateMaintenanceWindow(windowItem.id)
        toast.success('Maintenance activated')
      }
      load()
    } catch {
      toast.error('Toggle failed')
    }
  }

  if (loading) return <ListSkeleton rows={4} />

  if (hasError) {
    return (
      <ErrorState
        title="Maintenance windows unavailable"
        message="We could not load the current maintenance schedule."
        onRetry={load}
      />
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Maintenance Windows</h2>
        <button
          type="button"
          onClick={() => {
            setShowCreate((current) => !current)
            setFormErrors({})
          }}
          className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700"
        >
          <Plus size={16} />
          Schedule Maintenance
        </button>
      </div>

      {showCreate ? (
        <div className="space-y-4 rounded-xl border bg-white p-6">
          <h3 className="font-semibold">Schedule New Window</h3>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <FormField
              label="Title"
              htmlFor="maintenance-title"
              required
              error={formErrors.title}
              className="md:col-span-2"
            >
              <input
                id="maintenance-title"
                placeholder="Title"
                value={form.title}
                onChange={(event) => {
                  setForm((current) => ({ ...current, title: event.target.value }))
                  clearFormError('title')
                }}
                className="input-field"
                aria-invalid={formErrors.title ? true : undefined}
              />
            </FormField>
            <FormField
              label="Start"
              htmlFor="maintenance-start"
              required
              error={formErrors.scheduled_start}
            >
              <input
                id="maintenance-start"
                type="datetime-local"
                value={form.scheduled_start}
                onChange={(event) => {
                  setForm((current) => ({ ...current, scheduled_start: event.target.value }))
                  clearFormError('scheduled_start')
                }}
                className="input-field"
                aria-invalid={formErrors.scheduled_start ? true : undefined}
              />
            </FormField>
            <FormField
              label="End"
              htmlFor="maintenance-end"
              required
              error={formErrors.scheduled_end}
            >
              <input
                id="maintenance-end"
                type="datetime-local"
                value={form.scheduled_end}
                onChange={(event) => {
                  setForm((current) => ({ ...current, scheduled_end: event.target.value }))
                  clearFormError('scheduled_end')
                }}
                className="input-field"
                aria-invalid={formErrors.scheduled_end ? true : undefined}
              />
            </FormField>
            <TextArea
              id="maintenance-description"
              label="Description"
              value={form.description}
              onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
              className="md:col-span-2 min-h-[5rem]"
              rows={2}
              placeholder="Description"
              showCharacterCount={false}
            />
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={form.is_read_only} onChange={(e) => setForm((current) => ({ ...current, is_read_only: e.target.checked }))} />
            Read-only mode during maintenance
          </label>
          <div className="flex gap-2">
            <SubmitButton
              type="button"
              onClick={() => void handleCreate()}
              isLoading={isCreating}
              loadingText="Creating..."
            >
              Create
            </SubmitButton>
            <button
              type="button"
              onClick={() => {
                setShowCreate(false)
                setFormErrors({})
              }}
              className="btn-ghost"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : null}

      <div className="divide-y rounded-xl border bg-white">
        {windows.length === 0 ? (
          <div className="p-8">
            <EmptyState
              icon={<Clock className="h-8 w-8" aria-hidden="true" />}
              title="No maintenance scheduled"
              description="Schedule a maintenance window when you need to pause platform activity."
              action={{ label: 'Schedule Maintenance', onClick: () => setShowCreate(true) }}
            />
          </div>
        ) : windows.map((windowItem) => (
          <div key={windowItem.id} className="flex items-center justify-between p-4">
            <div>
              <div className="flex items-center gap-2">
                <p className="font-medium">{windowItem.title}</p>
                {windowItem.is_active ? (
                  <span className="animate-pulse rounded-full bg-red-100 px-2 py-0.5 text-xs text-red-700">ACTIVE</span>
                ) : null}
              </div>
              <p className="mt-1 text-xs text-slate-500">
                {new Date(windowItem.scheduled_start).toLocaleString()} {'->'} {new Date(windowItem.scheduled_end).toLocaleString()}
              </p>
              {windowItem.description ? <p className="mt-1 text-sm text-slate-600">{windowItem.description}</p> : null}
            </div>
            <button
              type="button"
              onClick={() => void handleToggle(windowItem)}
              className={`flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm ${
                windowItem.is_active
                  ? 'bg-green-600 text-white hover:bg-green-700'
                  : 'bg-red-600 text-white hover:bg-red-700'
              }`}
            >
              {windowItem.is_active ? (
                <>
                  <Square size={14} /> Deactivate
                </>
              ) : (
                <>
                  <Play size={14} /> Activate
                </>
              )}
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
