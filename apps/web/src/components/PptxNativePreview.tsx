import { useEffect, useRef, useState } from 'react'
import { AlertTriangle, Loader2 } from 'lucide-react'
import type { PptxViewer } from '@aiden0z/pptx-renderer'

interface PptxNativePreviewProps {
  /** PPTX bytes already fetched by the parent. */
  pptxBuffer: ArrayBuffer
  /** Optional initial slide index (0-based). */
  initialSlide?: number
  /** Callback when the viewer changes slide. */
  onSlideChange?: (index: number, total: number) => void
  /** External slide navigation trigger — set to desired 0-based index. */
  slideIndex?: number
}

/**
 * Browser-native PPTX renderer using @aiden0z/pptx-renderer.
 * Renders the actual PPTX bytes in a container div without server-side conversion.
 */
export default function PptxNativePreview({
  pptxBuffer,
  initialSlide = 0,
  onSlideChange,
  slideIndex,
}: PptxNativePreviewProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const viewerRef = useRef<PptxViewer | null>(null)
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading')
  const [errorMsg, setErrorMsg] = useState('')

  useEffect(() => {
    let cancelled = false
    const container = containerRef.current
    if (!container) return

    async function load() {
      try {
        const { PptxViewer, RECOMMENDED_ZIP_LIMITS } = await import('@aiden0z/pptx-renderer')
        if (cancelled) return
        const viewer = await PptxViewer.open(pptxBuffer, container, {
          zipLimits: RECOMMENDED_ZIP_LIMITS,
          listOptions: { windowed: true },
        })
        if (cancelled) {
          viewer.destroy()
          return
        }
        viewerRef.current = viewer
        if (initialSlide > 0) {
          await viewer.goToSlide(initialSlide)
        }
        setState('ready')
        onSlideChange?.(initialSlide, viewer.slideCount)
      } catch (err) {
        if (cancelled) return
        setState('error')
        setErrorMsg(err instanceof Error ? err.message : 'PPTX 渲染失败。')
      }
    }

    void load()
    return () => {
      cancelled = true
      viewerRef.current?.destroy()
      viewerRef.current = null
    }
    // Only run on mount/unmount — pptxBuffer identity is stable per artifact
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // External slide navigation
  useEffect(() => {
    const viewer = viewerRef.current
    if (viewer == null || slideIndex == null) return
    void viewer.goToSlide(slideIndex)
    onSlideChange?.(slideIndex, viewer.slideCount)
  }, [slideIndex, onSlideChange])

  if (state === 'error') {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-12 text-center">
        <AlertTriangle className="h-8 w-8 text-error" />
        <p className="text-sm font-bold text-on-surface">PPTX 渲染失败</p>
        <p className="text-xs text-on-surface-variant">{errorMsg}</p>
      </div>
    )
  }

  return (
    <div className="relative w-full">
      {state === 'loading' && (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-surface-container-lowest/80">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
        </div>
      )}
      <div ref={containerRef} className="w-full [&>div]:w-full [&_svg]:w-full [&_svg]:h-auto" />
    </div>
  )
}
