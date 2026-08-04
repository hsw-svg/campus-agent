import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import {
  Activity,
  ArrowRight,
  BarChart3,
  FileText,
  RefreshCw,
  UploadCloud,
  X,
  type LucideIcon,
} from 'lucide-react'

export type StandaloneTeacherAgentId = 'learning_analysis' | 'classroom_interaction' | 'course_iteration'

export interface TeacherAgentDefinition {
  id: StandaloneTeacherAgentId
  name: string
  description: string
  icon: LucideIcon
}

export const TEACHER_AGENT_DEFINITIONS: TeacherAgentDefinition[] = [
  {
    id: 'learning_analysis',
    name: '学情分析',
    description: '从匿名学习数据中提炼趋势、薄弱点与教学建议',
    icon: BarChart3,
  },
  {
    id: 'classroom_interaction',
    name: '课堂互动',
    description: '围绕主题和目标生成可直接使用的课堂活动序列',
    icon: Activity,
  },
  {
    id: 'course_iteration',
    name: '课程迭代',
    description: '根据教学主题与改进目标形成课程优化方案',
    icon: RefreshCw,
  },
]

interface PreparedTaskPayload {
  content: string
  files: File[]
}

interface TeacherAgentPreparationPanelProps {
  agentId: StandaloneTeacherAgentId
  isSubmitting: boolean
  onDirtyChange: (dirty: boolean) => void
  onSubmit: (payload: PreparedTaskPayload) => Promise<void>
}

const MAX_FILE_SIZE = 25 * 1024 * 1024
const GENERAL_EXTENSIONS = ['.txt', '.md', '.docx', '.pdf', '.xlsx', '.csv']

export default function TeacherAgentPreparationPanel({
  agentId,
  isSubmitting,
  onDirtyChange,
  onSubmit,
}: TeacherAgentPreparationPanelProps) {
  const definition = TEACHER_AGENT_DEFINITIONS.find((item) => item.id === agentId) ?? TEACHER_AGENT_DEFINITIONS[0]
  const Icon = definition.icon
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [topic, setTopic] = useState('')
  const [objective, setObjective] = useState('')
  const [focus, setFocus] = useState('')
  const [duration, setDuration] = useState('45')
  const [files, setFiles] = useState<File[]>([])
  const [validationError, setValidationError] = useState<string | null>(null)
  const accepts = agentId === 'learning_analysis' ? '.csv,.xlsx' : GENERAL_EXTENSIONS.join(',')
  const dirty = Boolean(topic.trim() || objective.trim() || focus.trim() || files.length > 0 || (agentId === 'classroom_interaction' && duration !== '45'))

  useEffect(() => onDirtyChange(dirty), [dirty, onDirtyChange])
  useEffect(() => () => onDirtyChange(false), [onDirtyChange])

  const canSubmit = useMemo(() => {
    if (isSubmitting) return false
    if (agentId === 'learning_analysis') return files.length > 0
    if (!topic.trim() || !objective.trim()) return false
    if (agentId === 'classroom_interaction') {
      const minutes = Number(duration || 45)
      return Number.isInteger(minutes) && minutes >= 5 && minutes <= 240
    }
    return true
  }, [agentId, duration, files.length, isSubmitting, objective, topic])

  const addFiles = (incoming: File[]) => {
    const allowedExtensions = agentId === 'learning_analysis' ? ['.csv', '.xlsx'] : GENERAL_EXTENSIONS
    const rejected = incoming.find((file) => {
      const extension = `.${file.name.split('.').pop()?.toLowerCase() ?? ''}`
      return !allowedExtensions.includes(extension) || file.size > MAX_FILE_SIZE
    })
    if (rejected) {
      setValidationError(`“${rejected.name}”格式不受支持或超过 25 MB。`)
      return
    }
    setValidationError(null)
    setFiles((current) => {
      const byIdentity = new Map(current.map((file) => [`${file.name}:${file.size}:${file.lastModified}`, file]))
      incoming.forEach((file) => byIdentity.set(`${file.name}:${file.size}:${file.lastModified}`, file))
      return [...byIdentity.values()]
    })
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    if (!canSubmit) {
      setValidationError(agentId === 'learning_analysis' ? '请先上传匿名 CSV 或 XLSX 学情表。' : '请完整填写教学主题和目标。')
      return
    }
    setValidationError(null)
    let content: string
    if (agentId === 'learning_analysis') {
      content = `分析学情${focus.trim() ? `，重点关注：${focus.trim()}` : ''}`
    } else if (agentId === 'classroom_interaction') {
      content = `生成课堂互动活动包：教学主题是${topic.trim()}，教学目标：${objective.trim()}，总时长 ${Number(duration || 45)} 分钟`
    } else {
      content = `课程迭代：教学主题是${topic.trim()}，迭代目标是${objective.trim()}。`
    }
    await onSubmit({ content, files })
  }

  return (
    <div className="relative z-10 mx-auto flex min-h-full w-full max-w-4xl items-start px-5 pb-10 pt-16 sm:px-8 sm:pb-12 sm:pt-20 lg:px-12">
      <form onSubmit={handleSubmit} className="w-full">
        <div className="flex items-start gap-5">
          <div className="flex min-w-0 items-start gap-4">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary text-on-primary shadow-[0_10px_28px_rgba(79,70,229,0.22)]">
              <Icon className="h-5 w-5" />
            </div>
            <div className="min-w-0 pt-0.5">
              <p className="text-[10px] font-black uppercase tracking-[0.18em] text-primary">教师 Agent · 独立任务</p>
              <h2 className="mt-1 font-display text-2xl font-black tracking-[-0.02em] text-on-surface sm:text-3xl">{definition.name}</h2>
              <p className="mt-1.5 max-w-2xl text-xs font-semibold leading-5 text-on-surface-variant sm:text-sm">{definition.description}。提交后将创建一个不关联课程的任务。</p>
            </div>
          </div>
        </div>

        <div className="mt-8 space-y-5 sm:mt-10">
          {agentId === 'learning_analysis' ? (
            <label className="block">
              <span className="text-xs font-extrabold text-on-surface">分析关注点 <span className="font-medium text-outline">（选填）</span></span>
              <textarea value={focus} onChange={(event) => setFocus(event.target.value)} rows={3} placeholder="例如：重点分析出勤率与作业成绩的关系" className="mt-2 w-full resize-none rounded-xl border border-outline-variant bg-surface-container-low px-3.5 py-3 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15" />
            </label>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block">
                <span className="text-xs font-extrabold text-on-surface">教学主题</span>
                <input value={topic} onChange={(event) => setTopic(event.target.value)} placeholder="例如：函数极限" className="mt-2 min-h-11 w-full rounded-xl border border-outline-variant bg-surface-container-low px-3.5 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15" required />
              </label>
              <label className="block">
                <span className="text-xs font-extrabold text-on-surface">{agentId === 'course_iteration' ? '迭代目标' : '教学目标'}</span>
                <input value={objective} onChange={(event) => setObjective(event.target.value)} placeholder={agentId === 'course_iteration' ? '例如：增强概念的直观理解' : '例如：理解极限的直观含义'} className="mt-2 min-h-11 w-full rounded-xl border border-outline-variant bg-surface-container-low px-3.5 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15" required />
              </label>
              {agentId === 'classroom_interaction' && (
                <label className="block sm:max-w-52">
                  <span className="text-xs font-extrabold text-on-surface">课堂时长 <span className="font-medium text-outline">（分钟）</span></span>
                  <input type="number" min={5} max={240} step={5} value={duration} onChange={(event) => setDuration(event.target.value)} className="mt-2 min-h-11 w-full rounded-xl border border-outline-variant bg-surface-container-low px-3.5 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15" />
                </label>
              )}
            </div>
          )}

          <section aria-labelledby="prepared-files-title" className="rounded-xl bg-surface/52 p-4 shadow-[0_10px_30px_rgba(25,28,26,0.035)] backdrop-blur-xl sm:p-5">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h3 id="prepared-files-title" className="text-xs font-extrabold text-on-surface">{agentId === 'learning_analysis' ? '匿名学情表' : '参考资料（选填）'}</h3>
                <p className="mt-1 text-[11px] leading-5 text-on-surface-variant">{agentId === 'learning_analysis' ? '支持 CSV、XLSX，至少上传一份。' : '支持 TXT、Markdown、DOCX、PDF、XLSX、CSV。'} 提交前文件不会上传。</p>
              </div>
              <button type="button" onClick={() => fileInputRef.current?.click()} className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-primary/25 bg-primary/5 px-3.5 text-xs font-bold text-primary transition hover:bg-primary/10 active:scale-[0.98]">
                <UploadCloud className="h-4 w-4" />选择文件
              </button>
              <input ref={fileInputRef} type="file" multiple accept={accepts} className="hidden" onChange={(event) => { addFiles(Array.from(event.target.files ?? [])); event.currentTarget.value = '' }} />
            </div>
            {files.length > 0 && (
              <div className="mt-3 space-y-2">
                {files.map((file) => (
                  <div key={`${file.name}:${file.size}:${file.lastModified}`} className="flex items-center gap-3 rounded-lg bg-surface-container-lowest px-3 py-2 text-xs shadow-xs">
                    <FileText className="h-4 w-4 shrink-0 text-primary" />
                    <span className="min-w-0 flex-1 truncate font-semibold text-on-surface">{file.name}</span>
                    <span className="shrink-0 text-[10px] text-outline">{Math.max(1, Math.round(file.size / 1024))} KB</span>
                    <button type="button" onClick={() => setFiles((current) => current.filter((item) => item !== file))} className="rounded-md p-1 text-outline hover:bg-error-container/40 hover:text-error" aria-label={`移除 ${file.name}`}><X className="h-3.5 w-3.5" /></button>
                  </div>
                ))}
              </div>
            )}
          </section>

          {validationError && <p role="alert" className="rounded-lg bg-error-container/45 px-3 py-2 text-xs font-semibold text-on-error-container">{validationError}</p>}
        </div>

        <div className="mt-7 flex justify-end">
          <button type="submit" disabled={!canSubmit} className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-primary px-5 text-xs font-extrabold text-on-primary shadow-sm transition hover:bg-primary/90 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-45">
            {isSubmitting ? '正在准备任务…' : '开始执行'}<ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </form>
    </div>
  )
}
