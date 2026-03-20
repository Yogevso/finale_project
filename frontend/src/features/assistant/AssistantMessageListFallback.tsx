import { MessageSkeleton } from '@/components/skeletons'

interface AssistantMessageListFallbackProps {
  rows?: number
  className?: string
}

export default function AssistantMessageListFallback({
  rows = 4,
  className = '',
}: AssistantMessageListFallbackProps) {
  return (
    <div className={['flex-1 overflow-y-auto', className].filter(Boolean).join(' ')}>
      <MessageSkeleton rows={rows} className="py-4" />
    </div>
  )
}
