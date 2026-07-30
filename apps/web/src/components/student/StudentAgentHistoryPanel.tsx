/**
 * StudentAgentHistoryPanel — student-side agent history side panel.
 *
 * This component is intentionally kept in apps/web/src/components/student/ and
 * imports only from student-specific modules. Do NOT import from
 * TeacherAgentHistoryPanel or any teacher/admin component — that is the
 * whole point of the student-dev branch separation.
 */

import { useState } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { X, Trash2, MoreVertical, Bot, Loader, AlertCircle, FileText } from 'lucide-react'
import type { StudentAgentHistoryItem } from '../../studentApi'

interface StudentAgentHistoryPanelProps {
  open: boolean
  history: StudentAgentHistoryItem[]
  loading: boolean
  error: string | null
  onClose: () => void
  onDeleteItem: (runId: string) => void
  onSelectItem?: (item: StudentAgentHistoryItem) => void
}

const AGENT_LABEL: Record<string, string> = {
  course_qa: '课程资料问答',
  personal_tutor: '个性化答疑',
  practice_helper: '练习助手',
  resume_helper: '简历助手',
  speaking_practice: '口语练习',
  study_planner: '学习规划',
}

function agentLabel(agentId: string | null): string {
  if (!agentId) return '智能助手'
  return AGENT_LABEL[agentId] ?? agentId
}

function statusColor(status: string): string {
  switch (status) {
    case 'completed': return 'text-emerald-600'
    case 'failed': return 'text-red-500'
    case 'running': return 'text-secondary'
    default: return 'text-on-surface-variant'
  }
}

// ─── Individual history item ─────────────────────────────────────────────────

interface HistoryItemProps {
  item: StudentAgentHistoryItem
  onDelete: (runId: string) => void
  onSelect?: (item: StudentAgentHistoryItem) => void
}

function HistoryItem({ item, onDelete, onSelect }: HistoryItemProps) {
  const [menuOpen, setMenuOpen] = useState(false)
  const [confirming, setConfirming] = useState(false)

  const handleDelete = () => {
    if (!confirming) {
      setConfirming(true)
      return
    }
    onDelete(item.run_id)
    setMenuOpen(false)
    setConfirming(false)
  }

  return (
    <div
      className="relative group bg-surface-container-lowest border border-outline-variant/60 rounded-xl p-3 hover:border-secondary/40 transition-colors cursor-pointer"
      onClick={() => onSelect?.(item)}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-7 h-7 rounded-lg bg-secondary-container/40 text-secondary flex items-center justify-center shrink-0">
            <Bot className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <p className="text-xs font-bold text-on-surface truncate">{agentLabel(item.agent_id)}</p>
            <p className="text-[10px] text-on-surface-variant truncate">{item.conversation_title}</p>
          </div>
        </div>

        {/* Three-dot menu */}
        <div className="relative shrink-0" onClick={(e) => e.stopPropagation()}>
          <button
            type="button"
            aria-label="更多操作"
            onClick={() => { setMenuOpen((v) => !v); setConfirming(false) }}
            className="p-1 rounded-md text-outline hover:text-secondary hover:bg-surface-container transition-colors"
          >
            <MoreVertical className="w-3.5 h-3.5" />
          </button>

          <AnimatePresence>
            {menuOpen && (
              <motion.div
                initial={{ opacity: 0, scale: 0.9, y: -4 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.9, y: -4 }}
                transition={{ duration: 0.1 }}
                className="absolute right-0 top-7 z-50 bg-surface border border-outline-variant rounded-xl shadow-lg overflow-hidden min-w-[140px]"
                onMouseLeave={() => { setMenuOpen(false); setConfirming(false) }}
              >
                <button
                  type="button"
                  onClick={handleDelete}
                  className={`w-full flex items-center gap-2 px-3 py-2 text-xs font-semibold transition-colors ${
                    confirming
                      ? 'text-red-600 bg-red-50 hover:bg-red-100'
                      : 'text-on-surface hover:bg-surface-container'
                  }`}
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  {confirming ? '确认删除' : '删除记录'}
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {item.summary && (
        <p className="mt-2 text-[11px] text-on-surface-variant leading-relaxed line-clamp-2 pl-9">
          {item.summary}
        </p>
      )}

      <div className="mt-2 pl-9 flex items-center gap-2">
        <span className={`text-[10px] font-semibold ${statusColor(item.status)}`}>
          {item.status === 'completed' ? '已完成' : item.status === 'failed' ? '失败' : item.status}
        </span>
        {item.artifact && (
          <span className="flex items-center gap-0.5 text-[10px] text-secondary font-semibold">
            <FileText className="w-3 h-3" />
            {item.artifact.title}
          </span>
        )}
        <span className="ml-auto text-[10px] text-outline">
          {new Date(item.created_at).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })}
        </span>
      </div>
    </div>
  )
}

// ─── Panel ───────────────────────────────────────────────────────────────────

export default function StudentAgentHistoryPanel({
  open,
  history,
  loading,
  error,
  onClose,
  onDeleteItem,
  onSelectItem,
}: StudentAgentHistoryPanelProps) {
  return (
    <AnimatePresence>
      {open && (
        <motion.aside
          initial={{ x: '100%', opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: '100%', opacity: 0 }}
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}
          className="fixed right-0 top-0 z-40 h-screen w-80 bg-surface-container-low border-l border-outline-variant flex flex-col shadow-xl"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-outline-variant shrink-0">
            <div className="flex items-center gap-2">
              <Bot className="w-4 h-4 text-secondary" />
              <span className="text-sm font-bold text-on-surface">智能助手记录</span>
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="关闭记录面板"
              className="p-1.5 rounded-lg text-outline hover:text-secondary hover:bg-surface-container transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {loading && (
              <div className="flex items-center justify-center py-12 gap-2 text-on-surface-variant">
                <Loader className="w-4 h-4 animate-spin" />
                <span className="text-xs">加载中…</span>
              </div>
            )}

            {!loading && error && (
              <div className="flex items-center gap-2 p-3 bg-error-container/30 rounded-xl text-on-error-container text-xs">
                <AlertCircle className="w-4 h-4 shrink-0" />
                {error}
              </div>
            )}

            {!loading && !error && history.length === 0 && (
              <div className="flex flex-col items-center justify-center py-12 text-center space-y-2">
                <Bot className="w-10 h-10 text-outline/40" />
                <p className="text-xs text-on-surface-variant font-medium">暂无智能助手记录</p>
                <p className="text-[10px] text-outline">在对话中使用智能助手后，记录将显示在这里</p>
              </div>
            )}

            {!loading && history.map((item) => (
              <HistoryItem
                key={item.run_id}
                item={item}
                onDelete={onDeleteItem}
                onSelect={onSelectItem}
              />
            ))}
          </div>
        </motion.aside>
      )}
    </AnimatePresence>
  )
}
