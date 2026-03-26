/**
 * CustomerRoute - thin wrapper over the shared RoleGuard implementation.
 */
import { CustomerGuard } from './RoleGuard'

interface CustomerRouteProps {
  children: React.ReactNode
}

export default function CustomerRoute({ children }: CustomerRouteProps) {
  return <CustomerGuard>{children}</CustomerGuard>
}
