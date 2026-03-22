/**
 * FeedbackForm - Reusable feedback submission form
 */
import { useState } from 'react'
import {
  HelpCircle,
  Lightbulb,
  AlertTriangle,
  MessageCircle,
} from 'lucide-react'
import { feedbackSchema } from '@/lib/validation/schemas'
import { validateForm } from '@/lib/validation'

interface FeedbackFormProps {
  onSubmit: (data: {
    feedback_type: 'question' | 'suggestion' | 'issue' | 'other'
    content: string
  }) => void
  isLoading?: boolean
  error?: string
}

const feedbackTypes = [
  { id: 'question', label: 'Question', icon: HelpCircle, color: 'blue' },
  { id: 'suggestion', label: 'Suggestion', icon: Lightbulb, color: 'yellow' },
  { id: 'issue', label: 'Report Issue', icon: AlertTriangle, color: 'red' },
  { id: 'other', label: 'Other', icon: MessageCircle, color: 'gray' },
] as const

export default function FeedbackForm({ onSubmit, isLoading, error }: FeedbackFormProps) {
  const [feedbackType, setFeedbackType] = useState<'question' | 'suggestion' | 'issue' | 'other'>('question')
  const [content, setContent] = useState('')
  const [validationError, setValidationError] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setValidationError('')
    const result = validateForm(feedbackSchema, { feedback_type: feedbackType, content: content.trim() })
    if (result.errors) {
      setValidationError(Object.values(result.errors)[0] || 'Please fix the form errors')
      return
    }
    onSubmit({ feedback_type: feedbackType, content: content.trim() })
  }

  const getColorClasses = (type: typeof feedbackTypes[number], isSelected: boolean) => {
    const colors = {
      blue: isSelected ? 'bg-sky-50 border-sky-500 text-sky-700' : 'hover:bg-sky-50',
      yellow: isSelected ? 'bg-amber-50 border-amber-500 text-amber-700' : 'hover:bg-amber-50',
      red: isSelected ? 'bg-rose-50 border-rose-500 text-rose-700' : 'hover:bg-rose-50',
      gray: isSelected ? 'bg-slate-100 border-slate-500 text-slate-700' : 'hover:bg-slate-50',
    }
    return colors[type.color]
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Feedback type selector */}
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-3">
          What type of feedback?
        </label>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {feedbackTypes.map((type) => {
            const isSelected = feedbackType === type.id
            return (
              <button
                key={type.id}
                type="button"
                onClick={() => setFeedbackType(type.id)}
                className={`flex flex-col items-center p-4 border-2 rounded-2xl transition-colors ${
                  isSelected ? 'border-2' : 'border-slate-200'
                } ${getColorClasses(type, isSelected)}`}
              >
                <type.icon className="h-6 w-6" />
                <span className="mt-2 text-sm font-medium">{type.label}</span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Content textarea */}
      <div>
        <label htmlFor="feedback-content" className="block text-sm font-medium text-slate-700 mb-2">
          Your feedback
        </label>
        <textarea
          id="feedback-content"
          rows={5}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Please provide details about your question, suggestion, or issue..."
          className="input-field resize-none"
          minLength={10}
          required
        />
        <p className="mt-1 text-sm text-slate-500">
          {content.length < 10 ? (
            `Minimum 10 characters required (${10 - content.length} more needed)`
          ) : (
            `${content.length} characters`
          )}
        </p>
      </div>

      {/* Error message */}
      {(error || validationError) && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-2xl text-rose-700 text-sm">
          {validationError || error}
        </div>
      )}

      {/* Submit button */}
      <div className="flex justify-end">
        <button
          type="submit"
          disabled={isLoading || content.trim().length < 10}
          className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
              Submitting...
            </>
          ) : (
            'Submit Feedback'
          )}
        </button>
      </div>
    </form>
  )
}
