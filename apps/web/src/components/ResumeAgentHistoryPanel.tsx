import { AnimatePresence, motion } from 'motion/react'
import { BriefcaseBusiness, ChevronDown, ChevronUp, FileClock, History, MoreVertical, Sparkles, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { ResumeAnalysisHistoryItem } from '../api'

interface ResumeAgentHistoryPanelProps {
  history: ResumeAnalysisHistoryItem[]
  activeRunId: string | null
  running: boolean
  onOpen: (item: ResumeAnalysisHistoryItem) => void
  onDelete: (runId: string) => void
}

export default function ResumeAgentHistoryPanel({
  history,
  activeRunId,
  running,
  onOpen,
  onDelete,
}: ResumeAgentHistoryPanelProps) {
  const [showAll, setShowAll] = useState(false)
  const shown = showAll ? history : history.slice(0, 6)

  return (
    <motion.aside
      initial={{ opacity: 0, x: 18 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ type: 'spring', bounce: 0, duration: 0.42 }}
      className="student-resume-history flex min-h-0 w-full flex-col gap-3 xl:h-full xl:overflow-y-auto xl:bg-surface-container-low/80 xl:p-3 xl:backdrop-blur-xl"
    >
      <section className="rounded-2xl border border-outline-variant/80 bg-surface-container-lowest/80 p-4 backdrop-blur-xl">
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 items-start gap-2.5">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-secondary/10 text-secondary">
              <History className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <p className="text-[10px] font-extrabold uppercase tracking-[0.16em] text-secondary">智能体记录</p>
              <h2 className="mt-0.5 text-sm font-black text-on-surface">简历优化历史</h2>
              <p className="mt-1 text-[10px] font-semibold leading-relaxed text-on-surface-variant">点击记录，在左侧恢复当次完整报告</p>
            </div>
          </div>
          <span className={`shrink-0 rounded-full px-2 py-1 text-[9px] font-extrabold ${running ? 'bg-secondary-container text-secondary' : 'bg-surface-container text-outline'}`}>
            {running ? '分析中' : `${history.length} 次`}
          </span>
        </div>
        {running && (
          <div className="mt-3 flex items-center gap-1.5 rounded-xl border border-secondary/20 bg-secondary/5 px-2.5 py-2 text-[10px] font-bold text-secondary">
            <Sparkles className="h-3.5 w-3.5 animate-pulse" />
            正在生成新的简历优化记录
          </div>
        )}
      </section>

      <section className="rounded-2xl border border-outline-variant/80 bg-surface-container-lowest/80 p-3 backdrop-blur-xl">
        {history.length === 0 ? (
          <div className="rounded-xl border border-dashed border-outline-variant px-4 py-8 text-center">
            <FileClock className="mx-auto h-6 w-6 text-outline" />
            <p className="mt-2 text-xs font-black text-on-surface">还没有分析记录</p>
            <p className="mt-1 text-[10px] leading-relaxed text-on-surface-variant">上传简历并点击“开始分析”后，报告会保存在这里。</p>
          </div>
        ) : (
          <div className="space-y-2">
            {shown.map((item, index) => (
              <motion.div
                key={item.run_id}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: Math.min(index, 5) * 0.035, duration: 0.22 }}
              >
                <HistoryItem
                  item={item}
                  active={activeRunId === item.run_id}
                  onOpen={() => onOpen(item)}
                  onDelete={() => onDelete(item.run_id)}
                />
              </motion.div>
            ))}
            {history.length > 6 && (
              <button
                type="button"
                onClick={() => setShowAll((current) => !current)}
                className="flex w-full items-center justify-center gap-1 pt-2 text-[10px] font-extrabold text-secondary"
              >
                {showAll ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                {showAll ? '收起历史记录' : `查看全部 ${history.length} 次记录`}
              </button>
            )}
          </div>
        )}
      </section>
    </motion.aside>
  )
}

function HistoryItem({
  item,
  active,
  onOpen,
  onDelete,
}: {
  item: ResumeAnalysisHistoryItem
  active: boolean
  onOpen: () => void
  onDelete: () => void
}) {
  const [menuOpen, setMenuOpen] = useState(false)
  const [confirming, setConfirming] = useState(false)

  useEffect(() => {
    if (!menuOpen) return
    const close = () => {
      setMenuOpen(false)
      setConfirming(false)
    }
    window.addEventListener('click', close)
    return () => window.removeEventListener('click', close)
  }, [menuOpen])

  return (
    <div className={`relative rounded-xl border px-3 py-2.5 transition-colors ${active ? 'border-secondary/50 bg-secondary/10 shadow-[inset_3px_0_0_#4ed8d0]' : 'border-outline-variant/70 bg-surface-container-low hover:border-secondary/30 hover:bg-secondary/5'}`}>
      <button type="button" onClick={onOpen} className="block w-full pr-5 text-left">
        <div className="flex items-start gap-2.5">
          <span className={`mt-1 h-2 w-2 shrink-0 rounded-full ${statusDot(item.status)}`} />
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-2">
              <p className="truncate text-[11px] font-black text-on-surface">{item.target_role || '通用简历优化'}</p>
              <span className="shrink-0 text-[9px] font-semibold text-outline">{formatTime(item.created_at)}</span>
            </div>
            <p className="mt-0.5 flex items-center gap-1 truncate text-[9px] font-bold text-secondary">
              <BriefcaseBusiness className="h-3 w-3 shrink-0" />
              {item.resume_filename || '简历文件'} · {statusLabel(item.status)}
            </p>
            {(item.summary || item.error_message) && (
              <p className={`mt-1 line-clamp-2 text-[9px] leading-relaxed ${item.error_message ? 'text-error' : 'text-on-surface-variant'}`}>
                {item.error_message || item.summary}
              </p>
            )}
          </div>
        </div>
      </button>

      <div className="absolute right-1.5 top-1.5">
        <button
          type="button"
          aria-label="更多操作"
          onClick={(event) => {
            event.stopPropagation()
            setConfirming(false)
            setMenuOpen((current) => !current)
          }}
          className="flex h-6 w-6 items-center justify-center rounded-md text-outline hover:bg-white/5 hover:text-on-surface"
        >
          <MoreVertical className="h-3.5 w-3.5" />
        </button>
        <AnimatePresence>
          {menuOpen && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: -4 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: -4 }}
              onClick={(event) => event.stopPropagation()}
              className="absolute right-0 top-7 z-20 w-32 overflow-hidden rounded-xl border border-outline-variant/70 bg-surface-container-lowest p-1 shadow-[0_16px_40px_rgba(0,5,20,0.45)]"
            >
              {confirming ? (
                <div className="p-1">
                  <p className="px-1 pb-1.5 text-[9px] font-bold text-on-surface-variant">确认删除该记录？</p>
                  <div className="flex gap-1">
                    <button type="button" onClick={onDelete} className="flex-1 rounded-lg bg-error px-2 py-1.5 text-[9px] font-extrabold text-white">删除</button>
                    <button type="button" onClick={() => setConfirming(false)} className="flex-1 rounded-lg bg-white/5 px-2 py-1.5 text-[9px] font-extrabold text-on-surface">取消</button>
                  </div>
                </div>
              ) : (
                <button type="button" disabled={item.status === 'running'} onClick={() => setConfirming(true)} className="flex w-full items-center gap-1.5 rounded-lg px-2 py-1.5 text-[10px] font-bold text-error hover:bg-error/10 disabled:opacity-40">
                  <Trash2 className="h-3 w-3" />删除记录
                </button>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

function statusDot(status: string): string {
  if (status === 'completed') return 'bg-secondary'
  if (status === 'running') return 'animate-pulse bg-tertiary'
  if (status === 'failed' || status === 'needs_input') return 'bg-error'
  return 'bg-outline'
}

function statusLabel(status: string): string {
  if (status === 'completed') return '已完成'
  if (status === 'running') return '执行中'
  if (status === 'failed') return '执行失败'
  if (status === 'needs_input') return '待补充输入'
  return '已记录'
}

function formatTime(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.valueOf())
    ? ''
    : date.toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}
