import { BookOpen, Check, Clipboard, Download, FileText, ListChecks, MessageCircleQuestion, Users } from 'lucide-react'
import { useState } from 'react'
import type { Artifact, SourceCitation } from '../api'

interface ArtifactCardProps {
  artifact: Artifact
  selected?: boolean
  selectable?: boolean
  onToggle?: () => void
  onExport: (artifact: Artifact, format: 'markdown' | 'csv') => Promise<void>
  sourceArtifacts?: Artifact[]
  citations?: SourceCitation[]
  key?: string
}

function textValue(value: unknown, fallback = '暂无'): string {
  if (typeof value === 'string' && value.trim()) return value
  if (typeof value === 'number') return String(value)
  return fallback
}

function listValue(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  return value.flatMap((item) => {
    if (typeof item === 'string') return [item]
    if (item && typeof item === 'object') {
      const record = item as Record<string, unknown>
      const content = record.content ?? record.text ?? record.action ?? record.criterion
      return typeof content === 'string' ? [content] : []
    }
    return []
  })
}

export default function ArtifactCard({
  artifact,
  selected = false,
  selectable = false,
  onToggle,
  onExport,
  sourceArtifacts = [],
  citations = [],
}: ArtifactCardProps) {
  const [copied, setCopied] = useState(false)
  const data = artifact.data ?? {}
  const isActivity = artifact.type === 'classroom_activity_package'
  const isObservation = artifact.type === 'classroom_observation'
  const isSummary = artifact.type === 'classroom_summary'
  const isCourseQA = artifact.type === 'course_qa'
  const isPersonalTutor = artifact.type === 'personal_tutor'
  const isMeetingMinutes = artifact.type === 'meeting_minutes'
  const isTodoBreakdown = artifact.type === 'todo_breakdown'

  const copyContent = async () => {
    await navigator.clipboard.writeText(artifact.content)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1600)
  }

  const icon = isActivity || isTodoBreakdown ? <ListChecks className="h-4 w-4" /> : isObservation ? <Users className="h-4 w-4" /> : isSummary || isMeetingMinutes ? <FileText className="h-4 w-4" /> : isCourseQA || isPersonalTutor ? <BookOpen className="h-4 w-4" /> : <MessageCircleQuestion className="h-4 w-4" />
  const status = typeof data.status === 'string' ? data.status : 'completed'
  const activities = Array.isArray(data.activities) ? data.activities as Record<string, unknown>[] : []
  const commonMisconceptions = listValue(data.common_misconceptions)
  const followUp = listValue(data.follow_up_practice)
  const adjustments = listValue(data.next_lesson_adjustments)

  return (
    <article className="rounded-2xl border border-outline-variant bg-[#FBFDFB] p-4 shadow-xs">
      <div className="flex items-start gap-3">
        <div className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${isObservation ? 'bg-secondary-container/40 text-secondary' : 'bg-primary/10 text-primary'}`}>
          {icon}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-extrabold text-on-surface">{artifact.title}</h3>
              <p className="mt-0.5 text-[10px] text-outline">{new Date(artifact.created_at).toLocaleString('zh-CN')}</p>
            </div>
            {selectable && onToggle && (
              <label className="flex shrink-0 cursor-pointer items-center gap-1.5 text-[10px] font-bold text-on-surface-variant">
                <input type="checkbox" checked={selected} onChange={onToggle} className="h-4 w-4 accent-primary" />
                引用
              </label>
            )}
          </div>

          {isActivity && (
            <div className="mt-3 space-y-3">
              <div className="flex flex-wrap items-center gap-2 text-[11px] font-bold text-on-surface-variant">
                <span className="rounded-full bg-primary/10 px-2.5 py-1 text-primary">{textValue(data.topic, '课堂互动')}</span>
                <span>总计 {textValue(data.total_minutes, '0')} / {textValue(data.duration_minutes, '0')} 分钟</span>
                {Boolean(data.validation && typeof data.validation === 'object' && (data.validation as Record<string, unknown>).partial) && (
                  <span className="rounded-full bg-tertiary-container/20 px-2.5 py-1 text-tertiary">部分题目已跳过</span>
                )}
              </div>
              <div className="space-y-2">
                {activities.map((activity, index) => (
                  <div key={String(activity.id ?? index)} className="rounded-xl border border-outline-variant/70 bg-white p-3">
                    <div className="flex items-center justify-between gap-2">
                      <h4 className="text-xs font-extrabold">{textValue(activity.title, `活动 ${index + 1}`)}</h4>
                      <span className="text-[10px] font-bold text-primary">{textValue(activity.duration_minutes, '0')} 分钟</span>
                    </div>
                    <p className="mt-1.5 text-xs leading-relaxed text-on-surface-variant">{textValue(activity.prompt)}</p>
                    {listValue(activity.options).length > 0 && <DetailList title="选项" items={listValue(activity.options)} />}
                    {textValue(activity.answer, '') && <p className="mt-2 text-[10px] font-bold text-primary">参考答案：{textValue(activity.answer, '')}</p>}
                    {textValue(activity.explanation, '') && <p className="mt-1 text-[10px] leading-relaxed text-on-surface-variant">解析：{textValue(activity.explanation, '')}</p>}
                    {textValue(activity.objective, '') && <p className="mt-2 text-[10px] text-on-surface-variant">目标：{textValue(activity.objective, '')}</p>}
                    {textValue(activity.teacher_prompt, '') && <p className="mt-2 rounded-lg bg-secondary-container/15 px-2.5 py-2 text-[10px] leading-relaxed text-secondary">教师提示语：{textValue(activity.teacher_prompt, '')}</p>}
                    {listValue(activity.common_misconceptions).length > 0 && (
                      <p className="mt-2 text-[10px] text-tertiary">常见误区：{listValue(activity.common_misconceptions).join('；')}</p>
                    )}
                    {listValue(activity.differentiated_hints).length > 0 && <DetailList title="分层提示" items={listValue(activity.differentiated_hints)} />}
                    {listValue(activity.rubric).length > 0 && <DetailList title="评分量规" items={listValue(activity.rubric)} />}
                    {listValue(activity.branches).length > 0 && <DetailList title="分支动作" items={listValue(activity.branches)} />}
                  </div>
                ))}
              </div>
            </div>
          )}

          {isObservation && (
            <div className="mt-3 space-y-3">
              {status === 'needs_confirmation' ? (
                <div className="rounded-xl border border-tertiary/30 bg-tertiary-container/15 p-3 text-xs text-tertiary">
                  <p className="font-extrabold">统计待确认，暂不继续分析</p>
                  {listValue(data.ambiguities).map((item) => <p key={item} className="mt-1">{item}</p>)}
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                  {Object.entries((data.counts ?? {}) as Record<string, unknown>).map(([option, count]) => {
                    const ratio = (data.ratios as Record<string, unknown> | undefined)?.[option]
                    return (
                      <div key={option} className="rounded-xl bg-surface-container p-2.5 text-center">
                        <p className="text-[10px] font-bold text-outline">选项 {option}</p>
                        <p className="mt-1 text-lg font-black text-primary">{textValue(count, '0')}</p>
                        <p className="text-[10px] text-on-surface-variant">{typeof ratio === 'number' ? `${(ratio * 100).toFixed(1)}%` : '—'}</p>
                      </div>
                    )
                  })}
                </div>
              )}
              <p className="text-xs leading-relaxed text-on-surface-variant">{textValue(data.note, artifact.content)}</p>
            </div>
          )}

          {isSummary && (
            <div className="mt-3 space-y-3">
              {sourceArtifacts.length > 0 && <div className="rounded-xl border border-primary/20 bg-primary/5 p-3"><p className="text-[10px] font-extrabold text-primary">本成果引用资料</p><p className="mt-1 text-[10px] leading-relaxed text-on-surface-variant">{sourceArtifacts.map((source) => source.title).join('、')}</p></div>}
              <SummarySection title="课堂摘要" value={textValue(data.classroom_summary)} />
              <SummarySection title="共同误区" items={commonMisconceptions} />
              <SummarySection title="教学策略反思" value={textValue(data.teaching_reflection)} />
              <SummarySection title="后续练习" items={followUp} />
              <SummarySection title="下次课调整项" items={adjustments} />
            </div>
          )}

          {isCourseQA && (
            <div className="mt-3 space-y-3">
              <SummarySection title="回答" value={textValue(data.answer, artifact.content)} />
              <SummarySection title="要点" items={listValue(data.key_points)} />
              <SummarySection title="追问" items={listValue(data.follow_up_questions)} />
            </div>
          )}

          {isPersonalTutor && (
            <div className="mt-3 space-y-3">
              <SummarySection title="诊断" value={textValue(data.diagnosis, artifact.content)} />
              <SummarySection title="讲解" value={textValue(data.explanation)} />
              <SummarySection title="易错点" items={listValue(data.mistakes)} />
              <SummarySection title="练习建议" items={listValue(data.practice)} />
              <SummarySection title="追问" items={listValue(data.follow_up_questions)} />
            </div>
          )}

          {isMeetingMinutes && (
            <div className="mt-3 space-y-3">
              <SummarySection title="议题" items={listValue(data.topics)} />
              <SummarySection title="决议" items={structuredList(data.decisions, 'decision')} />
              <SummarySection title="行动项" items={structuredList(data.action_items, 'task')} />
            </div>
          )}

          {isTodoBreakdown && (
            <div className="mt-3 space-y-3">
              <SummarySection title="待办项" items={structuredList(data.items, 'task', true)} />
            </div>
          )}

          {citations.length > 0 && (
            <div className="mt-3 rounded-xl border border-secondary/20 bg-secondary-container/10 p-3">
              <p className="text-[10px] font-extrabold text-secondary">本次任务实际引用 · {citations.length} 条</p>
              <ul className="mt-1.5 space-y-1.5 text-[10px] leading-relaxed text-on-surface-variant">
                {citations.map((citation, index) => (
                  <li key={`${citation.attachment_id}-${index}`}>
                    <span className="font-bold text-secondary">{citation.filename}{citation.page_number ? ` · 第 ${citation.page_number} 页` : ''}</span>
                    <span className="ml-1">{citation.excerpt}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {!isActivity && !isObservation && !isSummary && !isCourseQA && !isPersonalTutor && !isMeetingMinutes && !isTodoBreakdown && (
            <p className="mt-3 whitespace-pre-line text-xs leading-relaxed text-on-surface-variant">{artifact.content}</p>
          )}

          <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-outline-variant/60 pt-3">
            <button onClick={() => void copyContent()} className="inline-flex items-center gap-1.5 rounded-lg border border-outline-variant px-2.5 py-1.5 text-[10px] font-bold text-on-surface-variant hover:bg-surface-container" type="button">
              {copied ? <Check className="h-3.5 w-3.5 text-primary" /> : <Clipboard className="h-3.5 w-3.5" />}
              {copied ? '已复制' : '复制'}
            </button>
            <button onClick={() => void onExport(artifact, 'markdown')} className="inline-flex items-center gap-1.5 rounded-lg border border-outline-variant px-2.5 py-1.5 text-[10px] font-bold text-on-surface-variant hover:bg-surface-container" type="button">
              <Download className="h-3.5 w-3.5" /> Markdown
            </button>
            <button onClick={() => void onExport(artifact, 'csv')} className="inline-flex items-center gap-1.5 rounded-lg border border-outline-variant px-2.5 py-1.5 text-[10px] font-bold text-on-surface-variant hover:bg-surface-container" type="button">
              <Download className="h-3.5 w-3.5" /> CSV
            </button>
          </div>
        </div>
      </div>
    </article>
  )
}

function SummarySection({ title, value, items }: { title: string; value?: string; items?: string[] }) {
  const [copied, setCopied] = useState(false)
  const text = value ?? (items ?? []).join('\n')

  const copySection = async () => {
    if (!text) return
    await navigator.clipboard.writeText(text)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1400)
  }

  return (
    <section>
      <div className="flex items-center justify-between gap-2"><h4 className="text-[10px] font-extrabold uppercase tracking-wider text-primary">{title}</h4><button type="button" onClick={() => void copySection()} disabled={!text} className="text-[9px] font-bold text-outline hover:text-primary disabled:opacity-40">{copied ? '已复制' : '复制区块'}</button></div>
      {value && <p className="mt-1 text-xs leading-relaxed text-on-surface-variant">{value}</p>}
      {items && (
        <ul className="mt-1 space-y-1 text-xs leading-relaxed text-on-surface-variant">
          {items.length > 0 ? items.map((item) => <li key={item} className="flex gap-1.5"><span className="text-primary">•</span>{item}</li>) : <li>暂无</li>}
        </ul>
      )}
    </section>
  )
}

function DetailList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="mt-2 rounded-lg bg-surface-container/70 px-2.5 py-2">
      <p className="text-[10px] font-extrabold text-on-surface-variant">{title}</p>
      <ul className="mt-1 space-y-0.5 text-[10px] leading-relaxed text-on-surface-variant">
        {items.map((item) => <li key={item}>• {item}</li>)}
      </ul>
    </div>
  )
}

function structuredList(value: unknown, primaryKey: string, includePriority = false): string[] {
  if (!Array.isArray(value)) return []
  return value.flatMap((item) => {
    if (!item || typeof item !== 'object') return []
    const record = item as Record<string, unknown>
    const primary = record[primaryKey]
    if (typeof primary !== 'string' || !primary.trim()) return []
    const details = [
      typeof record.owner === 'string' && record.owner.trim() ? `负责人：${record.owner}` : '',
      typeof record.due_date === 'string' && record.due_date.trim() ? `截止：${record.due_date}` : '',
      includePriority && typeof record.priority === 'string' && record.priority.trim() ? `优先级：${record.priority}` : '',
      typeof record.evidence === 'string' && record.evidence.trim() ? `依据：${record.evidence}` : '',
    ].filter(Boolean)
    return [details.length > 0 ? `${primary}（${details.join('；')}）` : primary]
  })
}
