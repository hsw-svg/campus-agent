import { Activity, BookOpenCheck, Check, ChevronDown, ClipboardList, FileCheck2, GraduationCap, MessageCircleQuestion, Send } from 'lucide-react'
import { useMemo, useState, type ReactNode } from 'react'
import type { Artifact, Attachment, CourseContext } from '../api'

interface ClassroomInteractionPanelProps {
  courseContext: CourseContext
  attachments: Attachment[]
  artifacts: Artifact[]
  selectedArtifactIds: string[]
  onToggleArtifact: (artifactId: string) => void
  onPrompt: (content: string) => void
  onExport: (artifact: Artifact, format: 'markdown' | 'csv') => Promise<void>
  isBusy: boolean
}

type InteractionMode = 'activity' | 'observation' | 'summary'

function isLearningTable(attachment: Attachment): boolean {
  return /\.(csv|xlsx?|xls)$/i.test(attachment.filename)
    || /csv|spreadsheet|excel/i.test(attachment.content_type)
}

export default function ClassroomInteractionPanel({
  courseContext,
  attachments,
  artifacts,
  selectedArtifactIds,
  onToggleArtifact,
  onPrompt,
  onExport,
  isBusy,
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
  const selectedArtifacts = artifacts.filter((artifact) => selectedArtifactIds.includes(artifact.id))
  const hasLearningAnalysis = artifacts.some((artifact) => artifact.type === 'learning_analysis' || /learning.?analysis|学情/i.test(artifact.type))
  const hasActivityPackage = artifacts.some((artifact) => artifact.type === 'classroom_activity_package')
  const hasObservation = artifacts.some((artifact) => artifact.type === 'classroom_observation')
  const canAnalyzeLearning = courseContext.courseId !== null && attachments.some((attachment) =>
    isLearningTable(attachment) && ['indexed', 'degraded'].includes(attachment.status),
  )
  const workflowSteps = [
    { id: 'learning', label: '学情研判', detail: '识别班级薄弱点', done: hasLearningAnalysis },
    { id: 'activity', label: '课堂活动包', detail: '设计本节课互动', done: hasActivityPackage },
    { id: 'observation', label: '课堂观察', detail: '记录课堂反馈', done: hasObservation },
    { id: 'summary', label: '课后总结', detail: '沉淀教学调整', done: artifacts.some((artifact) => artifact.type === 'classroom_summary') },
  ]
  const hasPendingObservation = artifacts.some((artifact) => artifact.type === 'classroom_observation' && artifact.data.status === 'needs_confirmation')
  const canSummarize = selectedTypes.has('classroom_activity_package') && selectedTypes.has('classroom_observation') && !hasPendingObservation
  const hasObservationInput = observation.trim() || Object.values(optionCounts).some((count) => typeof count === 'string' && count.trim())
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
      <section className="rounded-2xl border border-primary/20 bg-white p-3 shadow-xs">
        <div className="flex items-start gap-2.5">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary"><GraduationCap className="h-4 w-4" /></div>
          <div className="min-w-0">
            <p className="text-[10px] font-extrabold uppercase tracking-wider text-primary">当前课程</p>
            <h3 className="mt-0.5 truncate text-sm font-black text-on-surface">{courseContext.courseName}</h3>
            <p className="mt-0.5 text-[10px] font-semibold text-on-surface-variant">{courseContext.workflowName}</p>
          </div>
        </div>
        <div className="mt-3 space-y-1.5">
          {workflowSteps.map((step, index) => {
            const isLearningStep = step.id === 'learning'
            const isActive = (isLearningStep && !step.done) || (!isLearningStep && mode === step.id)
            return (
              <button
                key={step.id}
                type="button"
                disabled={isLearningStep ? isBusy || (!step.done && !canAnalyzeLearning) : false}
                onClick={() => {
                  if (isLearningStep) onPrompt('分析学情')
                  else setMode(step.id as InteractionMode)
                }}
                className={`flex w-full items-center gap-2 rounded-xl px-2 py-1.5 text-left transition-colors ${isActive ? 'bg-primary/10' : 'hover:bg-surface-container'} disabled:cursor-not-allowed disabled:opacity-50`}
              >
                <span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[9px] font-black ${step.done ? 'bg-primary text-on-primary' : isActive ? 'border border-primary text-primary' : 'bg-surface-container-high text-outline'}`}>
                  {step.done ? <Check className="h-3 w-3" /> : index + 1}
                </span>
                <span className="min-w-0 flex-1">
                  <span className={`block text-[10px] font-extrabold ${isActive ? 'text-primary' : 'text-on-surface-variant'}`}>{step.label}</span>
                  <span className="block truncate text-[9px] text-outline">{step.detail}</span>
                </span>
                {isLearningStep && !step.done && <Activity className="h-3 w-3 text-primary" />}
              </button>
            )
          })}
        </div>
        {!canAnalyzeLearning && !hasLearningAnalysis && <p className="mt-2 rounded-lg bg-tertiary-container/20 px-2.5 py-2 text-[10px] leading-relaxed text-tertiary">当前课程暂无可用的学情表，请先上传并等待资料解析完成。</p>}
      </section>

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
            <p className="text-[10px] leading-relaxed text-outline">当前课程的全部资料会自动作为本次任务上下文；后端会校验题型、答案和总时长。</p>
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
