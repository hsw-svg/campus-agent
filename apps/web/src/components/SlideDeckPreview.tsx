import { useEffect, useMemo, useRef, useState } from 'react'
import {
  ChevronDown,
  ChevronRight,
  Copy,
  Download,
  FileCode,
  Layers,
  Link as LinkIcon,
  Presentation,
  Star,
} from 'lucide-react'
import type { Artifact } from '../api'
import Markdown from './Markdown'

interface Citation {
  title?: string
  url?: string
  snippet?: string
}

interface Slide {
  index: number
  layout: 'title' | 'bullets' | 'two_column' | 'callout' | 'summary' | string
  title?: string
  subtitle?: string
  bullets?: string[]
  left_bullets?: string[]
  right_bullets?: string[]
  left_title?: string
  right_title?: string
  callout?: string
  notes?: string
  key_points?: string[]
  citations?: Citation[]
}

interface SlideDeckData {
  topic?: string
  audience?: string
  objective?: string
  duration_minutes?: number
  context_signals?: Record<string, unknown>
  slides?: Slide[]
  sources?: Citation[]
}

interface SlideDeckPreviewProps {
  artifact: Artifact
  onExport?: (format: 'markdown' | 'pptx') => void
  onCopy?: (content: string) => void
}

function toStringList(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  return value.filter((item): item is string => typeof item === 'string' && item.length > 0)
}

function toCitationList(value: unknown): Citation[] {
  if (!Array.isArray(value)) return []
  return value.flatMap((item): Citation[] => {
    if (!item || typeof item !== 'object') return []
    const rec = item as Record<string, unknown>
    return [{
      title: typeof rec.title === 'string' ? rec.title : undefined,
      url: typeof rec.url === 'string' ? rec.url : undefined,
      snippet: typeof rec.snippet === 'string' ? rec.snippet : undefined,
    }]
  })
}

function normalizeSlides(value: unknown): Slide[] {
  if (!Array.isArray(value)) return []
  return value
    .map((item, idx): Slide | null => {
      if (!item || typeof item !== 'object') return null
      const rec = item as Record<string, unknown>
      const indexNum = typeof rec.index === 'number' ? rec.index : idx + 1
      const layoutStr = typeof rec.layout === 'string' ? rec.layout : 'bullets'
      return {
        index: indexNum,
        layout: layoutStr,
        title: typeof rec.title === 'string' ? rec.title : undefined,
        subtitle: typeof rec.subtitle === 'string' ? rec.subtitle : undefined,
        bullets: toStringList(rec.bullets),
        left_bullets: toStringList(rec.left_bullets),
        right_bullets: toStringList(rec.right_bullets),
        left_title: typeof rec.left_title === 'string' ? rec.left_title : undefined,
        right_title: typeof rec.right_title === 'string' ? rec.right_title : undefined,
        callout: typeof rec.callout === 'string' ? rec.callout : undefined,
        notes: typeof rec.notes === 'string' ? rec.notes : undefined,
        key_points: toStringList(rec.key_points),
        citations: toCitationList(rec.citations),
      }
    })
    .filter((slide): slide is Slide => slide !== null)
    .sort((a, b) => a.index - b.index)
}

export default function SlideDeckPreview({ artifact, onExport, onCopy }: SlideDeckPreviewProps) {
  const data = (artifact.data ?? {}) as SlideDeckData
  const slides = useMemo(() => normalizeSlides(data.slides), [data.slides])
  const total = slides.length
  const topic = typeof data.topic === 'string' && data.topic.length > 0 ? data.topic : (artifact.title || '未命名幻灯')
  const sources = useMemo(() => toCitationList(data.sources), [data.sources])

  const [currentIndex, setCurrentIndex] = useState(0)
  const [notesOpen, setNotesOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (currentIndex >= total && total > 0) {
      setCurrentIndex(0)
    }
  }, [total, currentIndex])

  if (total === 0) {
    return (
      <div className="w-full rounded-2xl border border-dashed border-outline-variant bg-surface-container-lowest px-6 py-8 text-center">
        <Presentation className="mx-auto mb-3 h-6 w-6 text-outline" />
        <p className="text-sm font-bold text-on-surface">暂无幻灯</p>
        <p className="mt-1 text-xs text-on-surface-variant">请再次触发生成，或在对话框输入修改意见后重试。</p>
      </div>
    )
  }

  const current = slides[Math.min(currentIndex, total - 1)]

  const handleKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'ArrowRight') {
      event.preventDefault()
      setCurrentIndex((idx) => Math.min(total - 1, idx + 1))
    } else if (event.key === 'ArrowLeft') {
      event.preventDefault()
      setCurrentIndex((idx) => Math.max(0, idx - 1))
    }
  }

  const handleCopyJson = () => {
    const jsonStr = JSON.stringify(artifact.data ?? {}, null, 2)
    if (onCopy) {
      onCopy(jsonStr)
    } else {
      void navigator.clipboard.writeText(jsonStr)
    }
  }

  return (
    <div
      ref={containerRef}
      tabIndex={0}
      onKeyDown={handleKeyDown}
      className="w-full overflow-hidden rounded-2xl border border-outline-variant/70 bg-[#FBFDFB] shadow-sm outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
    >
      {/* Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-outline-variant/60 bg-surface-container-low/50 px-5 py-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-primary">
            <Presentation className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <h3 className="truncate font-display text-sm font-extrabold text-on-surface md:text-base">{topic}</h3>
            <p className="text-[10px] font-semibold text-on-surface-variant">
              第 {current.index} 页 / 共 {total} 页{data.audience ? ` · ${data.audience}` : ''}{typeof data.duration_minutes === 'number' ? ` · ${data.duration_minutes} 分钟` : ''}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            type="button"
            onClick={() => onExport?.('pptx')}
            className="flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-[11px] font-bold text-on-primary hover:bg-primary-container"
          >
            <Download className="h-3.5 w-3.5" />
            下载 PPTX
          </button>
          <button
            type="button"
            onClick={() => onExport?.('markdown')}
            className="flex items-center gap-1.5 rounded-lg border border-outline-variant/70 px-3 py-1.5 text-[11px] font-bold text-on-surface hover:border-primary/40 hover:text-primary"
          >
            <FileCode className="h-3.5 w-3.5" />
            下载 MD
          </button>
          <button
            type="button"
            onClick={handleCopyJson}
            className="flex items-center gap-1.5 rounded-lg border border-outline-variant/70 px-3 py-1.5 text-[11px] font-bold text-on-surface hover:border-primary/40 hover:text-primary"
          >
            <Copy className="h-3.5 w-3.5" />
            复制 JSON
          </button>
        </div>
      </div>

      {/* Hint banner */}
      <div className="border-b border-outline-variant/40 bg-primary/10 px-5 py-2 text-[11px] font-semibold text-primary">
        在下方对话框输入修改意见，AI 会整份重生成幻灯。
      </div>

      {/* Body: thumbnails + main */}
      <div className="flex min-h-[26rem]">
        {/* Thumbnails */}
        <aside className="w-40 shrink-0 overflow-y-auto border-r border-outline-variant/50 bg-surface-container-lowest px-2 py-3 max-h-[32rem]">
          <p className="mb-2 px-1 text-[10px] font-extrabold uppercase tracking-wider text-outline">
            <Layers className="mr-1 inline h-3 w-3" />
            幻灯列表
          </p>
          <ul className="space-y-1.5">
            {slides.map((slide, idx) => {
              const active = idx === currentIndex
              return (
                <li key={`${slide.index}-${idx}`}>
                  <button
                    type="button"
                    onClick={() => setCurrentIndex(idx)}
                    className={`w-full rounded-lg border px-2 py-2 text-left transition ${
                      active
                        ? 'border-primary bg-primary/10 shadow-sm'
                        : 'border-outline-variant/60 bg-surface hover:border-primary/30'
                    }`}
                  >
                    <p className={`text-[10px] font-black tracking-wider ${active ? 'text-primary' : 'text-outline'}`}>
                      {String(slide.index).padStart(2, '0')}
                    </p>
                    <p className="mt-0.5 line-clamp-2 text-[11px] font-bold leading-snug text-on-surface">
                      {slide.title || `第 ${slide.index} 页`}
                    </p>
                  </button>
                </li>
              )
            })}
          </ul>
        </aside>

        {/* Main slide view */}
        <div className="flex min-w-0 flex-1 flex-col">
          <div className="flex-1 overflow-y-auto px-6 py-6">
            <SlideBody slide={current} />
          </div>

          {/* Speaker notes */}
          {current.notes && (
            <div className="border-t border-outline-variant/50 bg-surface-container-low/40 px-6 py-3">
              <button
                type="button"
                onClick={() => setNotesOpen((open) => !open)}
                className="flex w-full items-center justify-between gap-2 text-left text-[11px] font-bold text-on-surface-variant hover:text-primary"
                aria-expanded={notesOpen}
              >
                <span className="flex items-center gap-1.5">
                  {notesOpen ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                  演讲者备注
                </span>
                <span className="text-[10px] text-outline">Speaker Notes</span>
              </button>
              {notesOpen && (
                <div className="mt-2 rounded-lg bg-surface p-3">
                  <Markdown content={current.notes} className="text-xs leading-relaxed text-on-surface-variant" />
                </div>
              )}
            </div>
          )}

          {/* Citations */}
          {(current.citations && current.citations.length > 0) && (
            <div className="border-t border-outline-variant/50 bg-surface-container-lowest px-6 py-3">
              <p className="mb-2 text-[10px] font-extrabold uppercase tracking-wider text-outline">
                <LinkIcon className="mr-1 inline h-3 w-3" />
                引用
              </p>
              <ul className="flex flex-wrap gap-2">
                {current.citations.map((cite, idx) => (
                  <li key={`${cite.url ?? cite.title ?? idx}`}>
                    {cite.url ? (
                      <a
                        href={cite.url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex max-w-xs items-center gap-1 rounded-full border border-outline-variant/70 bg-surface px-2.5 py-1 text-[10px] font-semibold text-primary hover:border-primary/40"
                      >
                        <LinkIcon className="h-2.5 w-2.5" />
                        <span className="truncate">{cite.title || cite.url}</span>
                      </a>
                    ) : (
                      <span className="inline-flex max-w-xs items-center gap-1 rounded-full border border-outline-variant/70 bg-surface px-2.5 py-1 text-[10px] font-semibold text-on-surface-variant">
                        <span className="truncate">{cite.title || cite.snippet || '未命名引用'}</span>
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      {/* Global sources */}
      {sources.length > 0 && (
        <details className="border-t border-outline-variant/50 bg-surface-container-low/40 px-5 py-2">
          <summary className="cursor-pointer list-none text-[11px] font-bold text-primary marker:hidden">
            <span className="inline-flex items-center gap-1.5">
              整份幻灯的来源汇总（{sources.length}）
              <ChevronDown className="h-3 w-3" />
            </span>
          </summary>
          <ul className="mt-2 space-y-1.5">
            {sources.map((src, idx) => (
              <li key={`${src.url ?? src.title ?? idx}`} className="text-[11px] leading-relaxed">
                {src.url ? (
                  <a href={src.url} target="_blank" rel="noreferrer" className="font-semibold text-primary underline underline-offset-2">
                    {src.title || src.url}
                  </a>
                ) : (
                  <span className="font-semibold text-on-surface">{src.title || '未命名来源'}</span>
                )}
                {src.snippet && <span className="ml-1 text-on-surface-variant">— {src.snippet}</span>}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  )
}

function SlideBody({ slide }: { slide: Slide }) {
  const keyPoints = slide.key_points ?? []
  const layout = slide.layout

  if (layout === 'title') {
    return (
      <div className="flex h-full min-h-[20rem] flex-col items-center justify-center text-center">
        <p className="text-[10px] font-extrabold uppercase tracking-widest text-primary">
          Slide {String(slide.index).padStart(2, '0')} · Title
        </p>
        <h1 className="mt-4 font-display text-2xl font-black leading-tight text-on-surface md:text-3xl">
          {slide.title || '未命名'}
        </h1>
        {slide.subtitle && (
          <p className="mt-3 max-w-xl text-sm font-semibold text-on-surface-variant">{slide.subtitle}</p>
        )}
        {keyPoints.length > 0 && (
          <div className="mt-6 flex flex-wrap justify-center gap-2">
            {keyPoints.map((kp, idx) => (
              <KeyPointChip key={`${kp}-${idx}`} text={kp} />
            ))}
          </div>
        )}
      </div>
    )
  }

  if (layout === 'two_column') {
    return (
      <div className="space-y-4">
        <SlideHeader slide={slide} />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <ColumnBlock title={slide.left_title || '左侧'} bullets={slide.left_bullets ?? []} keyPoints={keyPoints} />
          <ColumnBlock title={slide.right_title || '右侧'} bullets={slide.right_bullets ?? []} keyPoints={keyPoints} />
        </div>
      </div>
    )
  }

  if (layout === 'callout') {
    return (
      <div className="space-y-4">
        <SlideHeader slide={slide} />
        {slide.callout && (
          <div className="rounded-2xl border-l-4 border-primary bg-primary/10 px-5 py-4">
            <p className="text-[10px] font-extrabold uppercase tracking-widest text-primary">重点提示</p>
            <div className="mt-1">
              <Markdown content={slide.callout} className="text-sm font-bold leading-relaxed text-on-surface" />
            </div>
          </div>
        )}
        {slide.bullets && slide.bullets.length > 0 && <BulletList bullets={slide.bullets} keyPoints={keyPoints} />}
        {keyPoints.length > 0 && !slide.callout && <KeyPointsRow points={keyPoints} />}
      </div>
    )
  }

  if (layout === 'summary') {
    return (
      <div className="space-y-4">
        <SlideHeader slide={slide} />
        <div className="rounded-2xl bg-secondary/5 p-4">
          <p className="mb-2 text-[10px] font-extrabold uppercase tracking-widest text-secondary">Summary</p>
          <BulletList bullets={slide.bullets ?? []} keyPoints={keyPoints} />
        </div>
        {keyPoints.length > 0 && <KeyPointsRow points={keyPoints} />}
      </div>
    )
  }

  // default: bullets
  return (
    <div className="space-y-4">
      <SlideHeader slide={slide} />
      <BulletList bullets={slide.bullets ?? []} keyPoints={keyPoints} />
      {keyPoints.length > 0 && <KeyPointsRow points={keyPoints} />}
    </div>
  )
}

function SlideHeader({ slide }: { slide: Slide }) {
  return (
    <div>
      <p className="text-[10px] font-extrabold uppercase tracking-widest text-primary">
        Slide {String(slide.index).padStart(2, '0')} · {slide.layout}
      </p>
      <h2 className="mt-1 font-display text-xl font-black leading-tight text-on-surface md:text-2xl">
        {slide.title || '未命名'}
      </h2>
      {slide.subtitle && <p className="mt-1 text-xs font-semibold text-on-surface-variant">{slide.subtitle}</p>}
    </div>
  )
}

function BulletList({ bullets, keyPoints }: { bullets: string[]; keyPoints: string[] }) {
  if (bullets.length === 0) {
    return <p className="text-xs italic text-outline">本页暂无要点内容。</p>
  }
  const keySet = new Set(keyPoints)
  return (
    <ul className="space-y-2">
      {bullets.map((bullet, idx) => {
        const isKey = keySet.has(bullet)
        return (
          <li
            key={`${bullet}-${idx}`}
            className={`flex items-start gap-2 rounded-lg px-3 py-2 ${
              isKey ? 'bg-error/5 border border-error/30' : 'bg-surface-container-lowest'
            }`}
          >
            {isKey ? (
              <Star className="mt-0.5 h-4 w-4 shrink-0 text-error" />
            ) : (
              <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-primary/70" />
            )}
            <div className="min-w-0 flex-1">
              <Markdown content={bullet} className={`text-sm leading-relaxed ${isKey ? 'font-bold text-on-surface' : 'text-on-surface'}`} />
            </div>
          </li>
        )
      })}
    </ul>
  )
}

function ColumnBlock({ title, bullets, keyPoints }: { title: string; bullets: string[]; keyPoints: string[] }) {
  return (
    <section className="rounded-2xl border border-outline-variant/50 bg-surface-container-lowest p-4">
      <p className="mb-2 text-[11px] font-extrabold text-primary">{title}</p>
      <BulletList bullets={bullets} keyPoints={keyPoints} />
    </section>
  )
}

function KeyPointsRow({ points }: { points: string[] }) {
  return (
    <div className="flex flex-wrap gap-2 pt-1">
      {points.map((point, idx) => (
        <KeyPointChip key={`${point}-${idx}`} text={point} />
      ))}
    </div>
  )
}

function KeyPointChip({ text }: { text: string }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-error/30 bg-error/10 px-2.5 py-1 text-[10px] font-bold text-error">
      <Star className="h-3 w-3" />
      {text}
    </span>
  )
}
