import VisibilityBadge from '@/components/VisibilityBadge'

const meta = {
  title: 'Components/VisibilityBadge',
  component: VisibilityBadge,
}

export default meta

export const Internal = {
  render: () => <VisibilityBadge visibility="internal" />,
}

export const Client = {
  render: () => <VisibilityBadge visibility="client" />,
}

export const Public = {
  render: () => <VisibilityBadge visibility="public" />,
}

export const Draft = {
  render: () => <VisibilityBadge visibility="draft" />,
}
