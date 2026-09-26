import { useI18n } from '../../i18n/core'
import { useEffect, useRef } from 'react'
import { Chart, LinearScale, PointElement, ScatterController, Tooltip } from 'chart.js'
import type { Point } from '../../services/trends'

Chart.register(ScatterController, PointElement, LinearScale, Tooltip)

export default function TrendChart({ points, unit, start, end }: { points: Point[]; unit: string; start: string; end: string }) {
  const { t } = useI18n()
  const canvas = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    if (!canvas.current) return
    const chart = new Chart(canvas.current, {
      type: 'scatter',
      data: { datasets: [{ label: unit, data: points.map(p => ({ x: Date.parse(p.day), y: Number(p.value) })), pointRadius: 5, pointHoverRadius: 7, backgroundColor: '#255c50' }] },
      options: {
        responsive: true, maintainAspectRatio: false, animation: false,
        scales: {
          x: { type: 'linear', min: Date.parse(start) - 43200000, max: Date.parse(end) + 43200000, title: { display: true, text: t('Measurement day') }, ticks: { maxTicksLimit: 7, callback: value => new Date(Number(value)).toISOString().slice(5, 10) } },
          y: { title: { display: true, text: unit } },
        },
        plugins: { tooltip: { callbacks: { title: items => points[items[0]?.dataIndex ?? 0]?.day ?? '', label: item => { const p = points[item.dataIndex]; return p ? t('{value} {unit} · {source} · revision {revision}', { value: p.raw_value, unit: p.unit, source: p.source_type === 'report' ? t('Published report') : t('Manual entry'), revision: p.revision }) : '' } } } },
      },
    })
    return () => chart.destroy()
  }, [points, unit, start, end, t])
  return <div className="trend-chart"><canvas ref={canvas} role="img" aria-label={t("{p0} real measurement points in {p1}, from {p2} to {p3}. Exact values and dates are in the measurement table below.", { p0: points.length, p1: unit, p2: start, p3: end })}>{t("The exact-value measurement table below contains every point.")}</canvas></div>
}
