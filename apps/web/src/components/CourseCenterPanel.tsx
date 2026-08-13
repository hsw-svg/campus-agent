import { ArrowRight, BookOpenCheck, CalendarDays, Clock3, LoaderCircle, Plus, RefreshCw, UserRound, X } from 'lucide-react'
import { motion } from 'motion/react'
import { useState, type FormEvent } from 'react'
import type { CourseSummary } from '../api'
import CourseArtwork from './CourseArtwork'

interface CourseCenterPanelProps {
  courses: CourseSummary[]
  loading: boolean
  error: string | null
  onRetry: () => void
  onOpen: (course: CourseSummary) => void
  onStart: (course: CourseSummary) => void
  onCreate: (name: string, description: string) => Promise<void>
}

export default function CourseCenterPanel({
  courses,
  loading,
  error,
  onRetry,
  onOpen,
  onStart,
  onCreate,
}: CourseCenterPanelProps) {
  const [createOpen, setCreateOpen] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)

  const submitCreate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!name.trim() || creating) return
    setCreating(true)
    setCreateError(null)
    try {
      await onCreate(name.trim(), description.trim())
      setName('')
      setDescription('')
      setCreateOpen(false)
    } catch (reason) {
      setCreateError(reason instanceof Error ? reason.message : '课程创建失败，请重试。')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="w-full py-3 sm:py-7">
      <div className="mb-7 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.24em] text-secondary">My learning</p>
          <h2 className="mt-2 font-display text-3xl font-black tracking-tight text-on-surface">课程中心</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-on-surface-variant">
            从通识基础出发，按章节进入 AI 辅导，让每一次学习都有清晰进度。
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-2 rounded-2xl border border-outline-variant/70 bg-surface-container-lowest px-4 py-3 text-xs font-bold text-on-surface-variant shadow-xs">
            <BookOpenCheck className="h-4 w-4 text-secondary" />
            {courses.length} 门课程 · {courses.filter((course) => course.started).length} 门学习中
          </div>
          <button type="button" onClick={() => setCreateOpen(true)} className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-secondary px-4 py-2.5 text-xs font-black text-on-secondary shadow-sm transition hover:opacity-90">
            <Plus className="h-4 w-4" />创建课程
          </button>
        </div>
      </div>

      {loading && (
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3" aria-label="正在加载课程">
          {Array.from({ length: 6 }, (_, index) => (
            <div key={index} className="h-96 animate-pulse rounded-3xl bg-surface-container" />
          ))}
        </div>
      )}

      {!loading && error && (
        <div className="rounded-3xl border border-error/25 bg-error-container/60 p-8 text-center">
          <p className="text-sm font-bold text-on-error-container">{error}</p>
          <button type="button" onClick={onRetry} className="mt-4 inline-flex items-center gap-2 rounded-xl bg-error px-4 py-2 text-xs font-black text-on-error">
            <RefreshCw className="h-4 w-4" />重新加载
          </button>
        </div>
      )}

      {!loading && !error && (
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
          {courses.map((course, index) => (
            <motion.article
              key={course.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.04 }}
              className="group overflow-hidden rounded-3xl border border-outline-variant/70 bg-surface-container-lowest shadow-xs transition-all hover:-translate-y-1 hover:border-secondary/35 hover:shadow-lg"
            >
              <button type="button" onClick={() => onOpen(course)} className="block w-full text-left">
                <CourseArtwork thumbnailKey={course.thumbnail_key} name={course.name} />
                <div className="p-5 pb-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <span className="rounded-full bg-secondary-container/35 px-2.5 py-1 text-[10px] font-black text-secondary">
                        {course.category ?? '通识课程'}
                      </span>
                      <h3 className="mt-3 text-lg font-black text-on-surface">{course.name}</h3>
                    </div>
                    <ArrowRight className="mt-1 h-5 w-5 text-outline transition-transform group-hover:translate-x-1 group-hover:text-secondary" />
                  </div>
                  <p className="mt-2 line-clamp-2 min-h-10 text-xs leading-5 text-on-surface-variant">{course.description}</p>
                  <div className="mt-4 grid grid-cols-2 gap-2 text-[11px] font-semibold text-on-surface-variant">
                    <span className="flex items-center gap-1.5"><UserRound className="h-3.5 w-3.5 text-secondary" />{course.teacher_name ?? '授课教师待定'}</span>
                    <span className="flex items-center gap-1.5"><CalendarDays className="h-3.5 w-3.5 text-secondary" />{formatDate(course.starts_at)}</span>
                    <span className="col-span-2 flex items-center gap-1.5"><Clock3 className="h-3.5 w-3.5 text-secondary" />{course.chapter_count} 个章节</span>
                  </div>
                </div>
              </button>
              <div className="border-t border-outline-variant/50 px-5 py-4">
                <div className="mb-3 flex items-center justify-between text-[10px] font-black">
                  <span className="text-on-surface-variant">{course.started ? `已完成 ${course.completed_chapter_count}/${course.chapter_count} 章` : '尚未开始'}</span>
                  <span className="text-secondary">{course.progress_percent}%</span>
                </div>
                <div className="mb-4 h-1.5 overflow-hidden rounded-full bg-surface-container-high">
                  <div className="h-full rounded-full bg-secondary transition-all" style={{ width: `${course.progress_percent}%` }} />
                </div>
                <button type="button" onClick={() => onStart(course)} className="flex w-full items-center justify-center gap-2 rounded-xl bg-secondary px-4 py-2.5 text-xs font-black text-on-secondary transition hover:opacity-90 active:scale-[0.98]">
                  {course.started ? '继续学习' : '开始学习'} <ArrowRight className="h-4 w-4" />
                </button>
              </div>
            </motion.article>
          ))}
        </div>
      )}

      {createOpen && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-scrim/55 p-4" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !creating) setCreateOpen(false) }}>
          <section role="dialog" aria-modal="true" aria-labelledby="create-student-course-title" className="w-full max-w-lg rounded-3xl border border-outline-variant bg-surface-container-lowest p-6 shadow-2xl">
            <header className="flex items-start justify-between gap-4">
              <div><p className="text-xs font-black uppercase tracking-[0.2em] text-secondary">New course</p><h3 id="create-student-course-title" className="mt-1 text-xl font-black text-on-surface">创建自己的课程</h3></div>
              <button type="button" disabled={creating} onClick={() => setCreateOpen(false)} className="grid h-11 w-11 place-items-center rounded-xl text-on-surface-variant hover:bg-surface-container" aria-label="关闭创建课程"><X className="h-5 w-5" /></button>
            </header>
            <form className="mt-6 space-y-4" onSubmit={(event) => { void submitCreate(event) }}>
              <label className="block text-xs font-black text-on-surface">课程名称<input autoFocus value={name} onChange={(event) => setName(event.target.value)} maxLength={160} placeholder="例如：线性代数自学" className="mt-2 h-12 w-full rounded-xl border border-outline-variant bg-surface px-4 text-sm font-semibold outline-none focus:border-secondary" /></label>
              <label className="block text-xs font-black text-on-surface">课程说明（可选）<textarea value={description} onChange={(event) => setDescription(event.target.value)} maxLength={2000} rows={4} placeholder="写下学习目标、适用阶段或重点内容" className="mt-2 w-full resize-none rounded-xl border border-outline-variant bg-surface px-4 py-3 text-sm leading-6 outline-none focus:border-secondary" /></label>
              {createError && <p role="alert" className="rounded-xl bg-error-container px-3 py-2 text-xs font-bold text-on-error-container">{createError}</p>}
              <button type="submit" disabled={!name.trim() || creating} className="flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-secondary px-5 text-sm font-black text-on-secondary disabled:opacity-50">{creating ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}{creating ? '正在创建课程' : '创建并进入课程'}</button>
            </form>
          </section>
        </div>
      )}
    </div>
  )
}

function formatDate(value: string | null): string {
  if (!value) return '开课时间待定'
  return new Intl.DateTimeFormat('zh-CN', { month: 'long', day: 'numeric' }).format(new Date(value))
}
