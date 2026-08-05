import {
  Activity,
  BarChart3,
  BookOpenText,
  ClipboardCheck,
  FileBarChart,
  FileOutput,
  History,
  MessageCircleQuestion,
  MoreVertical,
  Play,
  Sparkles,
  Trash2,
} from 'lucide-react'
import { AnimatePresence, LayoutGroup, motion } from 'motion/react'
import { useEffect, useId, useMemo, useState } from 'react'
import type { AgentHistoryItem, Artifact, Attachment, CourseContext } from '../api'
import type { TeacherAgentGroup, TeacherAgentId } from '../teacherAgents'
import { agentGroupFor, agentGroupForArtifactType, teacherAgentGroups } from '../teacherAgents'
import ClassroomInteractionPanel from './ClassroomInteractionPanel'

interface TeacherAgentHistoryPanelProps {
  courseContext: CourseContext
  attachments: Attachment[]
  artifacts: Artifact[]
  agentHistory: AgentHistoryItem[]
  activeAgentId: string | null
  activeConversationId: string | null
  selectedArtifactIds: string[]
  onToggleArtifact: (artifactId: string) => void
  onPrompt: (content: string) => void
  onExport: (artifact: Artifact, format: 'markdown' | 'csv' | 'pptx') => Promise<void>
  onViewHistoryItem: (item: AgentHistoryItem) => void
  onDeleteHistoryItem: (item: AgentHistoryItem) => void
  isBusy: boolean
}

const groupIcons: Record<TeacherAgentId, typeof Activity> = {
  learning_analysis: BarChart3,
  classroom_interaction: MessageCircleQuestion,
  course_iteration: BookOpenText,
  grading: ClipboardCheck,
  teaching_report: FileBarChart,
}

const quickActions: Record<Exclude<TeacherAgentId, 'classroom_interaction'>, { label: string; prompt: string }> = {
  learning_analysis: { label: '开始新的学情分析', prompt: '分析学情' },
  course_iteration: { label: '生成一次课程迭代', prompt: '根据最新学情分析更新课程内容，并生成下一课时的教案与练习题' },
  grading: { label: '开始作业批改', prompt: '批改这份作业，并给出评分建议、评语和错误归因' },
  teaching_report: { label: '生成教学报告', prompt: '生成教学报告' },
}

export default function TeacherAgentHistoryPanel({
  courseContext,
  attachments,
  artifacts,
  agentHistory,
  activeAgentId,
  activeConversationId,
  selectedArtifactIds,
  onToggleArtifact,
  onPrompt,
  onExport,
  onViewHistoryItem,
  onDeleteHistoryItem,
  isBusy,
}: TeacherAgentHistoryPanelProps) {
  const layoutGroupId = useId()
  const routedGroup = agentGroupFor(activeAgentId)
  const [selectedGroupId, setSelectedGroupId] = useState<TeacherAgentId>('learning_analysis')
  const [autoSwitchNotice, setAutoSwitchNotice] = useState<string | null>(null)
  const [showAllHistory, setShowAllHistory] = useState(false)

  useEffect(() => {
    if (!routedGroup) return
    setSelectedGroupId(routedGroup.id)
    setAutoSwitchNotice(`已根据最近一次任务切换到「${routedGroup.name}」`)
  }, [activeAgentId, routedGroup])

  const selectedGroup = teacherAgentGroups.find((group) => group.id === selectedGroupId) ?? teacherAgentGroups[0]
  const selectedHistory = useMemo(
    () => agentHistory.filter((item) => historyBelongsToGroup(item, selectedGroup)),
    [agentHistory, selectedGroup],
  )
  const currentGroupArtifacts = useMemo(
    () => artifacts.filter((artifact) => agentGroupForArtifactType(artifact.type)?.id === selectedGroup.id),
    [artifacts, selectedGroup.id],
  )
  const selectedAction = selectedGroup.id === 'classroom_interaction' ? null : quickActions[selectedGroup.id]
  const SelectedIcon = groupIcons[selectedGroup.id]

  const selectGroup = (group: TeacherAgentGroup) => {
    setSelectedGroupId(group.id)
    setAutoSwitchNotice(null)
    setShowAllHistory(false)
  }

  const shownHistory = showAllHistory ? selectedHistory : selectedHistory.slice(0, 6)

  return (
    <div
      className="flex h-full min-h-0 w-full min-w-0 flex-col gap-3 overflow-y-auto bg-surface-container-low/80 p-3 backdrop-blur-xl [scrollbar-gutter:stable]"
    >
      <section className="rounded-2xl border border-white/80 bg-white/75 p-3 shadow-[0_12px_32px_rgba(25,28,26,0.06)] backdrop-blur-xl">
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 items-start gap-2.5">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary"><History className="h-4.5 w-4.5" /></div>
            <div className="min-w-0">
              <p className="text-[10px] font-extrabold uppercase tracking-wider text-primary">智能体历史聚合</p>
              <h2 className="mt-0.5 truncate text-sm font-black text-on-surface">{courseContext.courseName}</h2>
              <p className="mt-0.5 text-[10px] font-semibold text-on-surface-variant">按智能体查看本课程的历次任务与成果索引</p>
            </div>
          </div>
          <span className={`shrink-0 rounded-full px-2 py-1 text-[9px] font-extrabold ${isBusy ? 'bg-secondary-container/40 text-secondary' : 'bg-surface-container text-outline'}`}>
            {isBusy ? '执行中' : `${agentHistory.length} 次记录`}
          </span>
        </div>
        {autoSwitchNotice && (
          <div className="mt-3 flex items-center gap-1.5 rounded-xl border border-primary/20 bg-primary/5 px-2.5 py-2 text-[10px] font-bold text-primary">
            <Sparkles className="h-3.5 w-3.5 shrink-0" />{autoSwitchNotice}
          </div>
        )}
      </section>

      <LayoutGroup id={layoutGroupId}>
        <div className="grid w-full min-w-0 grid-cols-5 gap-1 rounded-2xl border border-white/80 bg-white/65 p-1 shadow-xs backdrop-blur-xl">
          {teacherAgentGroups.map((group) => {
            const Icon = groupIcons[group.id]
            const count = agentHistory.filter((item) => historyBelongsToGroup(item, group)).length
            return (
              <motion.button
                key={group.id}
                type="button"
                onClick={() => selectGroup(group)}
                whileTap={{ scale: 0.96 }}
                className={`relative isolate flex min-w-0 flex-col items-center gap-1 rounded-xl px-1 py-2 text-center transition-colors ${selectedGroup.id === group.id ? 'text-on-primary' : 'text-on-surface-variant hover:bg-surface-container/80'}`}
                aria-label={`${group.name}，${count} 次记录`}
                aria-pressed={selectedGroup.id === group.id}
              >
                {selectedGroup.id === group.id && <motion.span layoutId="active-agent-tab" className="absolute inset-0 z-0 rounded-xl bg-primary shadow-[0_5px_14px_rgba(0,75,51,0.18)]" transition={{ type: 'spring', bounce: 0.12, duration: 0.35 }} />}
                <span className="relative z-10 flex w-full min-w-0 flex-col items-center gap-1"><Icon className="h-4 w-4 shrink-0" /><span className="w-full truncate text-[9px] font-extrabold">{group.shortName}</span><span className={`text-[8px] font-bold ${selectedGroup.id === group.id ? 'text-on-primary/75' : 'text-outline'}`}>{count}</span></span>
              </motion.button>
            )
          })}
        </div>
      </LayoutGroup>

      <section className="rounded-2xl border border-white/80 bg-[#FBFDFB]/85 p-3 shadow-[0_12px_32px_rgba(25,28,26,0.05)] backdrop-blur-xl">
        <div className="flex items-start justify-between gap-2">
          <div className="flex min-w-0 items-center gap-2">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary"><SelectedIcon className="h-4 w-4" /></div>
            <div className="min-w-0">
              <h3 className="truncate text-xs font-black text-on-surface">{selectedGroup.name}</h3>
              <p className="mt-0.5 text-[10px] leading-relaxed text-on-surface-variant">{selectedGroup.description}</p>
            </div>
          </div>
          {selectedHistory.length > 0 && <span className="shrink-0 text-[10px] font-bold text-outline">{selectedHistory.length} 次</span>}
        </div>

        {selectedHistory.length === 0 ? (
          <EmptyHistory group={selectedGroup} onPrompt={onPrompt} isBusy={isBusy} />
        ) : (
          <div className="mt-3 space-y-2">
            {shownHistory.map((item, index) => (
              <motion.div key={item.run_id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: Math.min(index, 5) * 0.035, duration: 0.22 }}>
                <HistoryItem
                  item={item}
                  isActive={item.conversation_id === activeConversationId}
                  onOpen={() => onViewHistoryItem(item)}
                  onDelete={() => onDeleteHistoryItem(item)}
                />
              </motion.div>
            ))}
            {selectedHistory.length > 6 && (
              <button type="button" onClick={() => setShowAllHistory((current) => !current)} className="w-full pt-1 text-center text-[10px] font-extrabold text-primary">
                {showAllHistory ? '收起历史记录' : `查看全部 ${selectedHistory.length} 次记录`}
              </button>
            )}
          </div>
        )}

        {currentGroupArtifacts.length > 0 && selectedHistory.length === 0 && (
          <p className="mt-2 text-[10px] text-outline">当前任务已有 {currentGroupArtifacts.length} 项成果，完成同步后会进入课程历史。</p>
        )}
        {selectedAction && (
          <button
            type="button"
            disabled={isBusy}
            onClick={() => onPrompt(selectedAction.prompt)}
            className="mt-3 inline-flex w-full items-center justify-center gap-1.5 rounded-xl bg-primary px-3 py-2.5 text-[10px] font-extrabold text-on-primary transition-opacity hover:opacity-95 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Play className="h-3.5 w-3.5" />{selectedAction.label}
          </button>
        )}
      </section>

      <AnimatePresence initial={false} mode="wait">
        {selectedGroup.id === 'classroom_interaction' && (
          <motion.section key="classroom-workflow" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }} className="rounded-2xl border border-white/80 bg-white/75 p-1 shadow-xs backdrop-blur-xl">
            <div className="flex items-center gap-2 px-3 pt-2 text-[10px] font-extrabold text-on-surface-variant">
              <Activity className="h-3.5 w-3.5 text-primary" />当前课堂工作流
            </div>
            <ClassroomInteractionPanel
              embedded
              courseContext={courseContext}
              attachments={attachments}
              artifacts={artifacts}
              selectedArtifactIds={selectedArtifactIds}
              onToggleArtifact={onToggleArtifact}
              onPrompt={onPrompt}
              onExport={onExport}
              isBusy={isBusy}
            />
          </motion.section>
        )}
      </AnimatePresence>
    </div>
  )
}

function historyBelongsToGroup(item: AgentHistoryItem, group: TeacherAgentGroup): boolean {
  return Boolean(agentGroupFor(item.agent_id)?.id === group.id || agentGroupForArtifactType(item.artifact?.type)?.id === group.id)
}

function EmptyHistory({ group, onPrompt, isBusy }: { group: TeacherAgentGroup; onPrompt: (content: string) => void; isBusy: boolean }) {
  const action = group.id === 'classroom_interaction' ? null : quickActions[group.id]
  return (
    <div className="mt-3 rounded-xl border border-dashed border-outline-variant px-3 py-5 text-center">
      <History className="mx-auto mb-1.5 h-5 w-5 text-outline" />
      <p className="text-[10px] font-bold text-on-surface-variant">本课程还没有{group.name}记录</p>
      {action && <button type="button" disabled={isBusy} onClick={() => onPrompt(action.prompt)} className="mt-3 rounded-lg border border-primary/30 px-2.5 py-1.5 text-[10px] font-extrabold text-primary disabled:opacity-40">{action.label}</button>}
      {group.id === 'classroom_interaction' && <p className="mt-2 text-[9px] text-outline">下方课堂工作流可直接生成活动包或记录课堂观察。</p>}
    </div>
  )
}

function HistoryItem({ item, isActive, onOpen, onDelete }: { item: AgentHistoryItem; isActive: boolean; onOpen: () => void; onDelete: () => void }) {
  const title = item.artifact?.title || item.conversation_title || '未命名教学任务'
  const time = formatHistoryTime(item.created_at)
  const status = statusLabel(item.status)
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
    <div className={`relative w-full rounded-xl border px-2.5 py-2 text-left transition-colors ${isActive ? 'border-primary/30 bg-primary/5' : 'border-outline-variant/70 bg-white hover:border-primary/30 hover:bg-primary/5'}`}>
      <button type="button" onClick={onOpen} className="block w-full text-left">
        <div className="flex items-start gap-2">
          <span className={`mt-1 h-2 w-2 shrink-0 rounded-full ${item.status === 'completed' ? 'bg-primary' : item.status === 'running' ? 'animate-pulse bg-secondary' : 'bg-outline'}`} />
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-2">
              <p className="truncate text-[10px] font-extrabold text-on-surface">{title}</p>
              <span className="shrink-0 pr-5 text-[9px] font-semibold text-outline">{time}</span>
            </div>
            <p className="mt-0.5 truncate text-[9px] font-bold text-primary">{status}{item.artifact ? ` · ${artifactLabel(item.artifact.type)}` : ' · 文本任务'}</p>
            {item.summary && <p className="mt-1 line-clamp-2 text-[9px] leading-relaxed text-on-surface-variant">{item.summary}</p>}
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
          className="flex h-5 w-5 items-center justify-center rounded-md text-outline transition-colors hover:bg-black/5 hover:text-on-surface"
        >
          <MoreVertical className="h-3.5 w-3.5" />
        </button>
        <AnimatePresence>
          {menuOpen && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: -4 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: -4 }}
              transition={{ duration: 0.12 }}
              onClick={(event) => event.stopPropagation()}
              className="absolute right-0 top-6 z-20 w-32 overflow-hidden rounded-xl border border-outline-variant/70 bg-white p-1 shadow-[0_12px_32px_rgba(25,28,26,0.12)]"
            >
              {confirming ? (
                <div className="p-1">
                  <p className="px-1 pb-1.5 text-[9px] font-bold text-on-surface-variant">确认删除该记录？</p>
                  <div className="flex gap-1">
                    <button
                      type="button"
                      onClick={() => {
                        setMenuOpen(false)
                        setConfirming(false)
                        onDelete()
                      }}
                      className="flex-1 rounded-lg bg-error px-2 py-1.5 text-[9px] font-extrabold text-on-error transition-opacity hover:opacity-90"
                    >
                      删除
                    </button>
                    <button
                      type="button"
                      onClick={() => setConfirming(false)}
                      className="flex-1 rounded-lg bg-black/5 px-2 py-1.5 text-[9px] font-extrabold text-on-surface transition-colors hover:bg-black/10"
                    >
                      取消
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => setConfirming(true)}
                  className="flex w-full items-center gap-1.5 rounded-lg px-2 py-1.5 text-[10px] font-bold text-error transition-colors hover:bg-error/10"
                >
                  <Trash2 className="h-3 w-3" />
                  删除记录
                </button>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

function formatHistoryTime(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.valueOf())) return ''
  return date.toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function statusLabel(status: string): string {
  switch (status) {
    case 'completed': return '已完成'
    case 'running': return '执行中'
    case 'needs_input': return '待补充输入'
    case 'failed': return '执行失败'
    case 'stopped': return '已停止'
    default: return '已记录'
  }
}

function artifactLabel(type: string): string {
  switch (type) {
    case 'learning_analysis': return '学情分析报告'
    case 'classroom_activity_package': return '课堂互动'
    case 'classroom_observation': return '课堂观察'
    case 'classroom_summary': return '课后总结'
    case 'lesson_design': return '教案与题目'
    case 'course_iteration': return '课程迭代'
    case 'grading': return '作业批改'
    case 'teaching_report': return '教学报告'
    default: return '结构化成果'
  }
}
