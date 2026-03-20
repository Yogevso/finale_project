import { useEffect, useState } from 'react'

type ChartTheme = {
  surface: string
  surfaceMuted: string
  border: string
  grid: string
  axis: string
  text: string
  textMuted: string
  tooltipBackground: string
  tooltipBorder: string
  series: string[]
}

const FALLBACK_THEME: ChartTheme = {
  surface: '#ffffff',
  surfaceMuted: '#f8fafc',
  border: '#e2e8f0',
  grid: '#e2e8f0',
  axis: '#64748b',
  text: '#0f172a',
  textMuted: '#475569',
  tooltipBackground: '#ffffff',
  tooltipBorder: '#dbe4f0',
  series: ['#0ea5e9', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'],
}

function readChartTheme(): ChartTheme {
  if (typeof window === 'undefined') {
    return FALLBACK_THEME
  }

  const styles = window.getComputedStyle(document.documentElement)
  const getValue = (name: string, fallback: string) => styles.getPropertyValue(name).trim() || fallback

  return {
    surface: getValue('--chart-surface', FALLBACK_THEME.surface),
    surfaceMuted: getValue('--chart-surface-muted', FALLBACK_THEME.surfaceMuted),
    border: getValue('--chart-border', FALLBACK_THEME.border),
    grid: getValue('--chart-grid', FALLBACK_THEME.grid),
    axis: getValue('--chart-axis', FALLBACK_THEME.axis),
    text: getValue('--chart-text', FALLBACK_THEME.text),
    textMuted: getValue('--chart-text-muted', FALLBACK_THEME.textMuted),
    tooltipBackground: getValue('--chart-tooltip-bg', FALLBACK_THEME.tooltipBackground),
    tooltipBorder: getValue('--chart-tooltip-border', FALLBACK_THEME.tooltipBorder),
    series: Array.from({ length: 8 }, (_, index) =>
      getValue(`--chart-series-${index + 1}`, FALLBACK_THEME.series[index] ?? FALLBACK_THEME.series[0]),
    ),
  }
}

export function useChartTheme() {
  const [theme, setTheme] = useState<ChartTheme>(readChartTheme)

  useEffect(() => {
    const refreshTheme = () => {
      setTheme(readChartTheme())
    }

    refreshTheme()
    window.addEventListener('themechange', refreshTheme)

    return () => {
      window.removeEventListener('themechange', refreshTheme)
    }
  }, [])

  return theme
}
