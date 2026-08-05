import { useEffect, useRef, useState } from 'react'
import { BrainCircuit, Check, ChevronDown, CircleAlert, LoaderCircle, Square } from 'lucide-react'
import type { AgentProgressStep } from '../api'

interface AgentProgressPanelProps {
  steps: AgentProgressStep[]
  isRunning: boolean
  runStatus: 'idle' | 'running' | 'completed' | 'needs_input' | 'failed' | 'stopped'
  onStop: () => void
}

function stepIcon(step: AgentProgressStep) {
  if (step.state === 'failed') return <CircleAlert className="h-3.5 w-3.5 text-error" />
  if (step.state === 'completed') return <Check className="h-3.5 w-3.5 text-primary" />
  return <LoaderCircle className="h-3.5 w-3.5 animate-spin text-primary motion-reduce:animate-none" />
}

export default function AgentProgressPanel({ steps, isRunning, runStatus, onStop }: AgentProgressPanelProps) {
  const [expanded, setExpanded] = useState(isRunning)
  const wasRunning = useRef(isRunning)

  useEffect(() => {
    if (isRunning) setExpanded(true)
    else if (wasRunning.current) setExpanded(false)
    wasRunning.current = isRunning
  }, [isRunning])

  if (steps.length === 0) return null

  const current = steps.find((step) => step.state === 'active') ?? steps[steps.length - 1]
  const failed = runStatus === 'failed' || runStatus === 'stopped' || steps.some((step) => step.state === 'failed')
  const summary = failed ? current.label : isRunning ? current.label : '智能体处理完成'

  return (
    <section
      aria-label="智能体执行进度"
      aria-live="polite"
      className="w-full max-w-md rounded-2xl border border-outline-variant/70 bg-surface-container-lowest/95 px-3 py-2 shadow-[0_10px_30px_rgba(25,28,26,0.08)] backdrop-blur-xl motion-reduce:transition-none"
    >
      <div className="flex items-center gap-2.5">
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <BrainCircuit className="h-4 w-4" />
        </span>
        <button
          type="button"
          onClick={() => setExpanded((value) => !value)}
          aria-expanded={expanded}
          className="min-w-0 flex-1 text-left outline-none focus-visible:ring-2 focus-visible:ring-primary/25"
        >
          <span className="block truncate text-xs font-extrabold text-on-surface">{summary}</span>
          <span className="mt-0.5 block text-[10px] font-semibold text-on-surface-variant">
            {isRunning ? '正在处理，可展开查看执行阶段' : `${steps.filter((step) => step.state === 'completed').length} 个阶段已完成`}
          </span>
        </button>
        {isRunning && (
          <button
            type="button"
            onClick={onStop}
            aria-label="停止生成"
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-outline transition-colors hover:bg-error/10 hover:text-error focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-error/25"
          >
            <Square className="h-3.5 w-3.5 fill-current" />
          </button>
        )}
        <button
          type="button"
          onClick={() => setExpanded((value) => !value)}
          aria-label={expanded ? '收起执行进度' : '展开执行进度'}
          className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-outline transition-transform hover:bg-surface-container-high hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/25 motion-reduce:transition-none ${expanded ? 'rotate-180' : ''}`}
        >
          <ChevronDown className="h-4 w-4" />
        </button>
      </div>

      {expanded && (
        <ol className="mt-2.5 space-y-1.5 border-t border-outline-variant/50 pt-2.5">
          {steps.map((step) => (
            <li key={step.id} className="flex min-w-0 items-start gap-2 text-[11px]">
              <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center">{stepIcon(step)}</span>
              <span className="min-w-0 flex-1">
                <span className={`block truncate font-bold ${step.state === 'failed' ? 'text-error' : 'text-on-surface'}`}>{step.label}</span>
                {step.detail && <span className="mt-0.5 block truncate font-semibold text-on-surface-variant">{step.detail}{step.count !== null ? ` · ${step.count}` : ''}</span>}
              </span>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
