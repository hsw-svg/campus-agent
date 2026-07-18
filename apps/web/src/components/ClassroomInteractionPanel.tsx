import { BookOpenCheck, ChevronDown, ClipboardList, FileCheck2, MessageCircleQuestion, Plus, Send, UploadCloud } from 'lucide-react'
import { useMemo, useState, type ReactNode } from 'react'
import type { Artifact, Attachment } from '../api'
import type { RouteState, RunStatus } from '../hooks/useWorkspaceChat'

interface ClassroomInteractionPanelProps {
  attachments: Attachment[]
  artifacts: Artifact[]
  selectedAttachmentIds: string[]
  selectedArtifactIds: string[]
  onToggleAttachment: (attachmentId: string) => void
  onToggleArtifact: (artifactId: string) => void
  onPrompt: (content: string) => void
  onUpload: (file: File) => Promise<void>
  onExport: (artifact: Artifact, format: 'markdown' | 'csv') => Promise<void>
  onStop: () => void
  onRetry: () => void
  isBusy: boolean
  runStatus: RunStatus
  toolStatus: string | null
  error: string | null
  route: RouteState | null
}

type InteractionMode = 'activity' | 'observation' | 'summary'

const statusLabel: Record<RunStatus, string> = {
  idle: '空闲',
  running: '执行中 · 详情在中间',
  completed: '已完成',
  needs_input: '需要补充',
  failed: '执行失败',
  stopped: '已停止',
}

export default function ClassroomInteractionPanel({
  attachments,
  artifacts,
  selectedAttachmentIds,
  selectedArtifactIds,
  onToggleAttachment,
  onToggleArtifact,
  onPrompt,
  onUpload,
  onExport,
  onStop,
  onRetry,
  isBusy,
  runStatus,
  toolStatus,
  error,
  route,
}: ClassroomInteractionPanelProps) {
  const [mode, setMode] = useState<InteractionMode>('activity')
  const [topic, setTopic] = useState('Python 列表索引与切片')
  const [objective, setObjective] = useState('区分索引和切片的返回结果，并能解释常见误区')
  const [duration, setDuration] = useState('45')
  const [observation, setObservation] = useState('')
  const [optionCounts, setOptionCounts] = useState<Record<string, string>>({ A: '', B: '', C: '', D: '' })
  const [declaredTotal, setDeclaredTotal] = useState('')
  const [showAllArtifacts, setShowAllArtifacts] = useState(false)

  const selectableArtifacts = useMemo(
    () => artifacts.filter((artifact) => ['classroom_activity_package', 'classroom_observation', 'classroom_summary'].includes(artifact.type)),
    [artifacts],
  )
  const shownArtifacts = showAllArtifacts ? selectableArtifacts : selectableArtifacts.slice(-3)
  const selectedCount = selectedArtifactIds.length
  const selectedTypes = new Set(
    artifacts.filter((artifact) => selectedArtifactIds.includes(artifact.id)).map((artifact) => artifact.type),
  )
  const selectedAttachments = attachments.filter((attachment) => selectedAttachmentIds.includes(attachment.id))
  const selectedArtifacts = artifacts.filter((artifact) => selectedArtifactIds.includes(artifact.id))
  const hasPendingObservation = artifacts.some((artifact) => artifact.type === 'classroom_observation' && artifact.data.status === 'needs_confirmation')
  const canSummarize = selectedTypes.has('classroom_activity_package') && selectedTypes.has('classroom_observation') && !hasPendingObservation
  const hasObservationInput = observation.trim() || Object.values(optionCounts).some((count) => typeof count === 'string' && count.trim())
  const attachmentGroups = [
    { scope: 'workspace' as const, title: '工作区资料库', items: attachments.filter((attachment) => attachment.scope === 'workspace') },
    { scope: 'conversation' as const, title: '当前对话附件', items: attachments.filter((attachment) => attachment.scope === 'conversation') },
  ]

  const submitActivity = () => {
    onPrompt(`生成课堂互动活动包：教学主题：${topic}；教学目标：${objective}；总时长：${duration} 分钟`)
  }

  const submitObservation = () => {
    const structuredCounts = Object.entries(optionCounts)
      .flatMap(([option, count]) => typeof count === 'string' && count.trim() ? [`${count.trim()} 人选 ${option}`] : [])
    const structuredText = structuredCounts.length > 0
      ? `${structuredCounts.join('、')}${declaredTotal.trim() ? `，总人数 ${declaredTotal.trim()} 人` : ''}`
      : ''
    const content = [structuredText, observation.trim()].filter(Boolean).join('；')
    if (content) onPrompt(`分析课堂观察：${content}`)
  }

  const submitSummary = () => onPrompt('生成课后总结')

  return (
    <div className="flex min-h-full w-full flex-col gap-4 overflow-y-auto bg-surface-container-low p-4">
      <div className="rounded-2xl border border-primary/20 bg-primary/5 p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-[10px] font-extrabold uppercase tracking-wider text-primary">阶段 7 · 教师单端</p>
            <h2 className="mt-1 text-base font-black text-on-surface">课堂互动闭环</h2>
            <p className="mt-1 text-xs leading-relaxed text-on-surface-variant">活动包 → 课堂观察 → 课后总结，所有资料都需明确选择。</p>
          </div>
          <div className={`rounded-full px-2 py-1 text-[10px] font-extrabold ${runStatus === 'failed' ? 'bg-error-container text-on-error-container' : runStatus === 'needs_input' ? 'bg-tertiary-container/25 text-tertiary' : 'bg-primary/10 text-primary'}`}>
            {statusLabel[runStatus]}
          </div>
        </div>
        {toolStatus && <p className="mt-3 border-t border-primary/15 pt-2 text-[10px] font-semibold text-primary">{toolStatus}</p>}
        {isBusy && <button type="button" onClick={onStop} className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-error/25 px-2.5 py-1.5 text-[10px] font-extrabold text-error hover:bg-error-container/30"><span className="h-2 w-2 rounded-sm bg-error" />停止当前任务</button>}
        {(runStatus === 'failed' || runStatus === 'needs_input') && !isBusy && <button type="button" onClick={onRetry} className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-primary/30 px-2.5 py-1.5 text-[10px] font-extrabold text-primary hover:bg-primary/10">重试上一次任务</button>}
        {error && <p role="alert" className="mt-3 rounded-lg border border-error/25 bg-error-container/30 px-2.5 py-2 text-[10px] font-bold leading-relaxed text-error">{error}</p>}
        {route && route.agentName && <p className="mt-3 border-t border-primary/15 pt-2 text-[10px] leading-relaxed text-on-surface-variant">已路由：<span className="font-extrabold text-primary">{route.agentName}</span> · {Math.round(route.confidence * 100)}%<br />{route.reason}</p>}
      </div>

      <div className="rounded-2xl border border-outline-variant bg-[#FBFDFB] p-3 shadow-xs">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-[11px] font-extrabold uppercase tracking-wider text-on-surface-variant">课堂任务</h3>
          <span className="text-[10px] font-bold text-outline">已选成果 {selectedCount}</span>
        </div>
        <div className="grid grid-cols-3 gap-1 rounded-xl bg-surface-container p-1">
          <ModeButton active={mode === 'activity'} onClick={() => setMode('activity')} icon={<BookOpenCheck className="h-3.5 w-3.5" />} label="活动包" />
          <ModeButton active={mode === 'observation'} onClick={() => setMode('observation')} icon={<MessageCircleQuestion className="h-3.5 w-3.5" />} label="观察" />
          <ModeButton active={mode === 'summary'} onClick={() => setMode('summary')} icon={<FileCheck2 className="h-3.5 w-3.5" />} label="总结" />
        </div>

        {mode === 'activity' && (
          <div className="mt-3 space-y-2.5">
            <Field label="教学主题" value={topic} onChange={setTopic} />
            <label className="block text-[10px] font-bold text-on-surface-variant">
              本节课目标
              <textarea value={objective} onChange={(event) => setObjective(event.target.value)} rows={2} className="mt-1 w-full resize-none rounded-lg border border-outline-variant bg-white px-2.5 py-2 text-xs text-on-surface outline-none focus:border-primary" />
            </label>
            <div className="flex items-end gap-2">
              <label className="block flex-1 text-[10px] font-bold text-on-surface-variant">总时长（分钟）<input value={duration} onChange={(event) => setDuration(event.target.value)} inputMode="numeric" className="mt-1 w-full rounded-lg border border-outline-variant bg-white px-2.5 py-2 text-xs outline-none focus:border-primary" /></label>
              <button disabled={isBusy || !topic.trim() || !objective.trim()} onClick={submitActivity} type="button" className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-[10px] font-extrabold text-on-primary disabled:cursor-not-allowed disabled:opacity-40"><Send className="h-3.5 w-3.5" />生成</button>
            </div>
            <p className="text-[10px] leading-relaxed text-outline">请在下方“资料选择”中勾选课程资料；后端会校验题型、答案和总时长。</p>
          </div>
        )}

        {mode === 'observation' && (
          <div className="mt-3 space-y-2.5">
            <label className="block text-[10px] font-bold text-on-surface-variant">匿名课堂观察或选项统计<textarea value={observation} onChange={(event) => setObservation(event.target.value)} rows={4} placeholder="例如：8 人选 A、21 人选 B、5 人选 C，大部分学生解释不清索引与切片" className="mt-1 w-full resize-none rounded-lg border border-outline-variant bg-white px-2.5 py-2 text-xs leading-relaxed outline-none focus:border-primary" /></label>
            <div>
              <p className="mb-1 text-[10px] font-bold text-on-surface-variant">结构化选项统计（可选）</p>
              <div className="grid grid-cols-4 gap-1.5">
                {Object.entries(optionCounts).map(([option, count]) => (
                  <label key={option} className="text-[10px] font-bold text-outline">{option}<input value={count} onChange={(event) => setOptionCounts((current) => ({ ...current, [option]: event.target.value }))} inputMode="numeric" placeholder="人数" className="mt-1 w-full rounded-lg border border-outline-variant bg-white px-2 py-1.5 text-xs text-on-surface outline-none focus:border-primary" /></label>
                ))}
              </div>
              <label className="mt-2 block text-[10px] font-bold text-outline">声明总人数（用于校验）<input value={declaredTotal} onChange={(event) => setDeclaredTotal(event.target.value)} inputMode="numeric" placeholder="可留空" className="mt-1 w-full rounded-lg border border-outline-variant bg-white px-2.5 py-1.5 text-xs text-on-surface outline-none focus:border-primary" /></label>
            </div>
            <button disabled={isBusy || !hasObservationInput} onClick={submitObservation} type="button" className="inline-flex w-full items-center justify-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-[10px] font-extrabold text-on-primary disabled:cursor-not-allowed disabled:opacity-40"><MessageCircleQuestion className="h-3.5 w-3.5" />分析课堂观察</button>
            <p className="text-[10px] leading-relaxed text-outline">统计由后端计算；如果存在多组人数或总数冲突，会先要求确认。</p>
          </div>
        )}

        {mode === 'summary' && (
          <div className="mt-3 space-y-2.5">
            <div className="rounded-xl border border-secondary/20 bg-secondary-container/15 p-3 text-xs leading-relaxed text-on-surface-variant">请选择一个活动包和一条课堂观察记录，再生成课后总结。</div>
            <button disabled={isBusy || !canSummarize} onClick={submitSummary} type="button" className="inline-flex w-full items-center justify-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-[10px] font-extrabold text-on-primary disabled:cursor-not-allowed disabled:opacity-40"><FileCheck2 className="h-3.5 w-3.5" />生成课后总结</button>
            {!canSummarize && <p className="text-[10px] text-outline">需要同时引用活动包和课堂观察成果。</p>}
          </div>
        )}
      </div>

      <section className="rounded-2xl border border-outline-variant bg-[#FBFDFB] p-3 shadow-xs">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-[11px] font-extrabold uppercase tracking-wider text-on-surface-variant">资料选择</h3>
          <label className="inline-flex cursor-pointer items-center gap-1 rounded-lg border border-outline-variant px-2 py-1 text-[10px] font-bold text-primary hover:bg-surface-container">
            <Plus className="h-3 w-3" /> 上传
            <input type="file" className="hidden" accept=".csv,.xlsx,.xls,.pdf,.doc,.docx,.txt,.md" onChange={(event) => { const file = event.target.files?.[0]; if (file) void onUpload(file); event.currentTarget.value = '' }} />
          </label>
        </div>
        {attachments.length === 0 ? (
          <div className="rounded-xl border border-dashed border-outline-variant p-4 text-center text-[10px] text-outline"><UploadCloud className="mx-auto mb-1 h-5 w-5" />暂无可选资料</div>
        ) : (
          <div className="max-h-56 space-y-3 overflow-y-auto">
            {attachmentGroups.map((group) => (
              <div key={group.scope}>
                <p className="mb-1.5 px-1 text-[10px] font-extrabold text-on-surface-variant">{group.title}</p>
                {group.items.length === 0 ? (
                  <p className="rounded-lg bg-surface-container px-2.5 py-2 text-[10px] text-outline">
                    {group.scope === 'conversation' ? '当前对话暂无附件，可从工作区资料库中勾选。' : '工作区资料库暂无资料。'}
                  </p>
                ) : group.items.map((attachment) => (
                  <label key={attachment.id} className="mb-1.5 flex cursor-pointer items-center gap-2 rounded-xl border border-outline-variant/60 bg-white px-2.5 py-2 hover:border-primary/50">
                    <input type="checkbox" checked={selectedAttachmentIds.includes(attachment.id)} onChange={() => onToggleAttachment(attachment.id)} className="h-3.5 w-3.5 accent-primary" />
                    <span className="min-w-0 flex-1 truncate text-[10px] font-bold text-on-surface">{attachment.filename}</span>
                    <span className={`text-[9px] ${attachment.status === 'failed' ? 'text-error' : attachment.status === 'indexed' ? 'text-primary' : 'text-outline'}`}>{attachment.status === 'indexed' ? '可用' : attachment.status}</span>
                  </label>
                ))}
              </div>
            ))}
          </div>
        )}
        <div className="mt-2 rounded-lg bg-secondary-container/15 px-2.5 py-2 text-[10px] leading-relaxed text-on-surface-variant">
          <p className="font-extrabold text-secondary">当前任务资料 · {selectedAttachments.length} 项</p>
          <p className="mt-0.5 text-outline">上传不等于使用；只有勾选资料才会随本次任务发送。</p>
          {selectedAttachments.length > 0 && <p className="mt-1 truncate text-primary">{selectedAttachments.map((attachment) => attachment.filename).join('、')}</p>}
        </div>
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between px-1">
          <h3 className="text-[11px] font-extrabold uppercase tracking-wider text-on-surface-variant">课堂成果</h3>
          {selectableArtifacts.length > 3 && <button onClick={() => setShowAllArtifacts((current) => !current)} type="button" className="inline-flex items-center gap-1 text-[10px] font-bold text-primary">{showAllArtifacts ? '收起' : '查看全部'}<ChevronDown className={`h-3 w-3 transition-transform ${showAllArtifacts ? 'rotate-180' : ''}`} /></button>}
        </div>
        {selectedArtifacts.length > 0 && <div className="rounded-xl border border-primary/20 bg-primary/5 px-3 py-2 text-[10px] leading-relaxed text-primary"><p className="font-extrabold">当前任务成果 · {selectedArtifacts.length} 项</p><p className="mt-0.5 truncate">{selectedArtifacts.map((artifact) => artifact.title).join('、')}</p></div>}
        {hasPendingObservation && <div className="rounded-xl border border-tertiary/30 bg-tertiary-container/15 px-3 py-2 text-[10px] leading-relaxed text-tertiary"><p className="font-extrabold">课堂观察需要确认</p><p className="mt-0.5">请回到“观察”输入，补充选项归属或修正总人数后重新提交。</p><button type="button" onClick={() => setMode('observation')} className="mt-2 rounded-lg border border-tertiary/30 px-2 py-1 font-extrabold hover:bg-tertiary-container/25">去补充观察</button></div>}
        {shownArtifacts.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-outline-variant p-5 text-center text-[10px] text-outline"><ClipboardList className="mx-auto mb-1 h-5 w-5" />生成活动包或课堂观察后，成果会显示在这里。</div>
        ) : shownArtifacts.map((artifact) => (
          <div key={artifact.id} className="flex items-center gap-2 rounded-xl border border-outline-variant/70 bg-white px-3 py-2.5">
            {artifact.type !== 'classroom_summary' && (
              <input
                type="checkbox"
                checked={selectedArtifactIds.includes(artifact.id)}
                onChange={() => onToggleArtifact(artifact.id)}
                className="h-3.5 w-3.5 accent-primary"
                aria-label={`选择成果：${artifact.title}`}
              />
            )}
            <div className="min-w-0 flex-1">
              <p className="truncate text-[10px] font-extrabold text-on-surface">{artifact.title}</p>
              <p className="mt-0.5 text-[9px] text-outline">{artifactTypeLabel(artifact.type)} · 已在中间对话区展示详情</p>
            </div>
            <button
              type="button"
              onClick={() => void onExport(artifact, 'markdown')}
              className="shrink-0 rounded-lg border border-outline-variant px-2 py-1 text-[9px] font-extrabold text-primary hover:bg-primary/5"
            >
              导出
            </button>
          </div>
        ))}
        {selectedCount > 0 && (
          <button disabled={isBusy} onClick={() => onPrompt('生成后续练习')} type="button" className="inline-flex w-full items-center justify-center gap-1.5 rounded-lg border border-primary/30 bg-primary/5 px-3 py-2 text-[10px] font-extrabold text-primary disabled:cursor-not-allowed disabled:opacity-40">
            <ClipboardList className="h-3.5 w-3.5" />基于已选成果生成后续练习
          </button>
        )}
      </section>
    </div>
  )
}

function ModeButton({ active, onClick, icon, label }: { active: boolean; onClick: () => void; icon: ReactNode; label: string }) {
  return <button type="button" onClick={onClick} className={`flex items-center justify-center gap-1 rounded-lg px-1.5 py-2 text-[10px] font-extrabold transition-colors ${active ? 'bg-white text-primary shadow-xs' : 'text-outline hover:text-primary'}`}>{icon}{label}</button>
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return <label className="block text-[10px] font-bold text-on-surface-variant">{label}<input value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 w-full rounded-lg border border-outline-variant bg-white px-2.5 py-2 text-xs outline-none focus:border-primary" /></label>
}

function artifactTypeLabel(type: string): string {
  switch (type) {
    case 'classroom_activity_package':
      return '课堂活动包'
    case 'classroom_observation':
      return '课堂观察'
    case 'classroom_summary':
      return '课后总结'
    default:
      return '课堂成果'
  }
}
