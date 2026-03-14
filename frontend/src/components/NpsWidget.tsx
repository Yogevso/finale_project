import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { X, MessageSquareHeart } from 'lucide-react'
import { portalApi } from '@/lib/portalApi'

const SCORE_LABELS: Record<number, string> = {
  0: 'Not at all likely',
  5: 'Neutral',
  10: 'Extremely likely',
}

export function NpsWidget() {
  const queryClient = useQueryClient()
  const [dismissed, setDismissed] = useState(false)
  const [selectedScore, setSelectedScore] = useState<number | null>(null)
  const [comment, setComment] = useState('')
  const [submitted, setSubmitted] = useState(false)

  const { data: status } = useQuery({
    queryKey: ['nps-status'],
    queryFn: () => portalApi.getNpsStatus(),
    staleTime: 10 * 60 * 1000,
  })

  const submitMutation = useMutation({
    mutationFn: () => portalApi.submitNps(selectedScore!, comment || undefined),
    onSuccess: () => {
      setSubmitted(true)
      queryClient.invalidateQueries({ queryKey: ['nps-status'] })
    },
  })

  if (dismissed || !status?.should_show) return null

  if (submitted) {
    return (
      <div className="fixed bottom-6 right-6 z-50 w-80 surface-card rounded-2xl shadow-2xl border border-slate-200 p-6 animate-in slide-in-from-bottom-4">
        <div className="text-center">
          <MessageSquareHeart className="h-10 w-10 text-emerald-500 mx-auto mb-3" />
          <h3 className="font-display font-semibold text-slate-900">Thank you!</h3>
          <p className="text-sm text-slate-500 mt-1">Your feedback helps us improve.</p>
          <button
            onClick={() => setDismissed(true)}
            className="mt-4 text-sm text-sky-600 hover:text-sky-700"
          >
            Close
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 w-96 surface-card rounded-2xl shadow-2xl border border-slate-200 animate-in slide-in-from-bottom-4">
      <div className="flex items-center justify-between px-5 py-3 border-b border-slate-100">
        <h3 className="font-display font-semibold text-slate-900 text-sm">Quick Survey</h3>
        <button
          onClick={() => setDismissed(true)}
          className="text-slate-400 hover:text-slate-600"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="p-5 space-y-4">
        <p className="text-sm text-slate-700">
          How likely are you to recommend this platform to a colleague?
        </p>

        {/* Score buttons */}
        <div>
          <div className="flex gap-1">
            {Array.from({ length: 11 }, (_, i) => (
              <button
                key={i}
                onClick={() => setSelectedScore(i)}
                className={`flex-1 py-2 text-xs font-medium rounded-lg transition-colors ${
                  selectedScore === i
                    ? i <= 6
                      ? 'bg-red-500 text-white'
                      : i <= 8
                        ? 'bg-amber-500 text-white'
                        : 'bg-emerald-500 text-white'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {i}
              </button>
            ))}
          </div>
          <div className="flex justify-between mt-1">
            <span className="text-[10px] text-slate-400">{SCORE_LABELS[0]}</span>
            <span className="text-[10px] text-slate-400">{SCORE_LABELS[10]}</span>
          </div>
        </div>

        {selectedScore !== null && (
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Any additional feedback? (optional)"
            rows={2}
            className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-sky-500 resize-none"
          />
        )}

        <button
          onClick={() => submitMutation.mutate()}
          disabled={selectedScore === null || submitMutation.isPending}
          className="w-full py-2 text-sm font-medium text-white bg-sky-600 rounded-xl hover:bg-sky-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {submitMutation.isPending ? 'Submitting...' : 'Submit'}
        </button>
      </div>
    </div>
  )
}
