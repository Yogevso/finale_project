import type { ReactNode } from 'react'
import { useLocation } from 'react-router-dom'

interface RouteTransitionProps {
  children: ReactNode
}

export default function RouteTransition({ children }: RouteTransitionProps) {
  const location = useLocation()
  const routeKey = `${location.pathname}${location.search}${location.hash}`

  return (
    <div key={routeKey} className="motion-enter-fade min-h-0">
      {children}
    </div>
  )
}
