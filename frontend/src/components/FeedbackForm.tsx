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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (content.trim().length < 10) return
    onSubmit({ feedback_type: feedbackType, content: content.trim() })
  }

  const getColorClasses = (type: typeof feedbackTypes[number], isSelected: boolean) => {
    const colors = {
      blue: isSelected ? 'bg-blue-100 border-blue-500 text-blue-700' : 'hover:bg-blue-50',
      yellow: isSelected ? 'bg-yellow-100 border-yellow-500 text-yellow-700' : 'hover:bg-yellow-50',
      red: isSelected ? 'bg-red-100 border-red-500 text-red-700' : 'hover:bg-red-50',
      gray: isSelected ? 'bg-gray-100 border-gray-500 text-gray-700' : 'hover:bg-gray-50',
    }
    return colors[type.color]
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Feedback type selector */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-3">
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
                className={`flex flex-col items-center p-4 border-2 rounded-lg transition-colors ${
                  isSelected ? 'border-2' : 'border-gray-200'
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
        <label htmlFor="feedback-content" className="block text-sm font-medium text-gray-700 mb-2">
          Your feedback
        </label>
        <textarea
          id="feedback-content"
          rows={5}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Please provide details about your question, suggestion, or issue..."
          className="w-full px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
          minLength={10}
          required
        />
        <p className="mt-1 text-sm text-gray-500">
          {content.length < 10 ? (
            `Minimum 10 characters required (${10 - content.length} more needed)`
          ) : (
            `${content.length} characters`
          )}
        </p>
      </div>

      {/* Error message */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Submit button */}
      <div className="flex justify-end">
        <button
          type="submit"
          disabled={isLoading || content.trim().length < 10}
          className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
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
