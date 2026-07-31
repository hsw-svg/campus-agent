import { ArrowLeft, ArrowRight, BookOpen, CheckCircle2, Clock3, Lightbulb, Play, Sparkles, Target } from 'lucide-react'
import type { CourseDetail } from '../api'
import CourseArtwork from './CourseArtwork'

interface CourseDetailPanelProps {
  course: CourseDetail
  loading: boolean
  onBack: () => void
  onStart: (chapterId?: string) => void
}

export default function CourseDetailPanel({ course, loading, onBack, onStart }: CourseDetailPanelProps) {
  const current = course.chapters.find((chapter) => chapter.id === course.current_chapter_id)
    ?? course.chapters.find((chapter) => !chapter.completed)
    ?? course.chapters[0]

  return (
    <div className="w-full py-3 sm:py-7">
      <button type="button" onClick={onBack} className="mb-5 inline-flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-black text-on-surface-variant hover:bg-surface-container">
        <ArrowLeft className="h-4 w-4" />返回课程中心
      </button>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.5fr)_minmax(280px,0.7fr)]">
        <div className="space-y-6">
          <CourseArtwork thumbnailKey={course.thumbnail_key} name={course.name} compact />

          <section className="rounded-3xl border border-outline-variant/70 bg-surface-container-lowest p-5 sm:p-7">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="text-xs font-black text-secondary">{course.category ?? '通识课程'} · {course.teacher_name ?? '授课教师待定'}</p>
                <h2 className="mt-2 text-2xl font-black text-on-surface">{course.name}</h2>
                <p className="mt-3 max-w-2xl text-sm leading-6 text-on-surface-variant">{course.description}</p>
              </div>
              <button disabled={loading || !current} type="button" onClick={() => onStart(current?.id)} className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-secondary px-5 py-3 text-xs font-black text-on-secondary shadow-sm disabled:opacity-50">
                <Play className="h-4 w-4 fill-current" />{course.started ? '继续学习' : '开始学习'}
              </button>
            </div>
          </section>

          <section className="rounded-3xl border border-outline-variant/70 bg-surface-container-lowest p-5 sm:p-7">
            <div className="mb-5 flex items-center justify-between">
              <div>
                <p className="text-xs font-black uppercase tracking-[0.18em] text-secondary">Course outline</p>
                <h3 className="mt-1 text-xl font-black text-on-surface">课程章节</h3>
              </div>
              <span className="text-xs font-bold text-on-surface-variant">{course.completed_chapter_count}/{course.chapter_count} 已完成</span>
            </div>
            <div className="space-y-3">
              {course.chapters.map((chapter) => (
                <button
                  key={chapter.id}
                  type="button"
                  onClick={() => onStart(chapter.id)}
                  disabled={loading}
                  className={`group flex w-full items-start gap-4 rounded-2xl border p-4 text-left transition ${
                    chapter.current
                      ? 'border-secondary/40 bg-secondary-container/15'
                      : 'border-outline-variant/60 hover:border-secondary/30 hover:bg-surface-container-low'
                  }`}
                >
                  <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-xs font-black ${
                    chapter.completed ? 'bg-secondary text-on-secondary' : 'bg-surface-container-high text-on-surface-variant'
                  }`}>
                    {chapter.completed ? <CheckCircle2 className="h-4 w-4" /> : chapter.position}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center justify-between gap-3">
                      <span className="font-black text-on-surface">{chapter.title}</span>
                      <span className="flex shrink-0 items-center gap-1 text-[10px] font-bold text-outline"><Clock3 className="h-3 w-3" />{chapter.estimated_minutes ?? 45} 分钟</span>
                    </span>
                    <span className="mt-1 block text-xs leading-5 text-on-surface-variant">{chapter.summary}</span>
                    <span className="mt-2 flex flex-wrap gap-1.5">
                      {chapter.knowledge_points.map((point) => <span key={point} className="rounded-full bg-surface-container px-2 py-1 text-[9px] font-bold text-on-surface-variant">{point}</span>)}
                    </span>
                  </span>
                  <ArrowRight className="mt-2 h-4 w-4 shrink-0 text-outline group-hover:text-secondary" />
                </button>
              ))}
            </div>
          </section>
        </div>

        <aside className="space-y-5">
          <section className="rounded-3xl border border-outline-variant/70 bg-surface-container-lowest p-5">
            <div className="flex items-center gap-2"><Target className="h-5 w-5 text-secondary" /><h3 className="font-black text-on-surface">学习进度</h3></div>
            <div className="mt-5 flex items-end justify-between"><span className="text-4xl font-black text-secondary">{course.progress_percent}%</span><span className="text-[11px] font-bold text-on-surface-variant">{course.started ? '持续学习中' : '准备开始'}</span></div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-surface-container-high"><div className="h-full rounded-full bg-secondary" style={{ width: `${course.progress_percent}%` }} /></div>
            {current && <div className="mt-4 rounded-2xl bg-secondary-container/15 p-3"><p className="text-[10px] font-black text-secondary">当前章节</p><p className="mt-1 text-xs font-bold text-on-surface">{current.title}</p></div>}
          </section>

          <section className="rounded-3xl border border-outline-variant/70 bg-surface-container-lowest p-5">
            <div className="flex items-center gap-2"><Lightbulb className="h-5 w-5 text-tertiary" /><h3 className="font-black text-on-surface">薄弱知识点推荐</h3></div>
            {course.weak_points.length === 0 ? (
              <div className="mt-4 rounded-2xl border border-dashed border-outline-variant bg-surface-container-low p-5 text-center">
                <Sparkles className="mx-auto h-6 w-6 text-outline" />
                <p className="mt-2 text-xs font-bold text-on-surface">暂无学习诊断</p>
                <p className="mt-1 text-[10px] leading-5 text-on-surface-variant">完成章节学习或测验后，AI 会根据真实学习成果给出建议。</p>
              </div>
            ) : (
              <div className="mt-4 space-y-3">
                {course.weak_points.map((point) => (
                  <div key={point.id} className="rounded-2xl bg-tertiary-container/15 p-4">
                    <p className="text-xs font-black text-on-surface">{point.name}</p>
                    <p className="mt-2 text-[11px] leading-5 text-on-surface-variant">{point.recommendation}</p>
                  </div>
                ))}
              </div>
            )}
          </section>

          <button disabled={loading || !current} type="button" onClick={() => onStart(current?.id)} className="flex w-full items-center justify-center gap-2 rounded-2xl bg-secondary px-5 py-4 text-sm font-black text-on-secondary shadow-md disabled:opacity-50">
            <BookOpen className="h-5 w-5" />{course.started ? '继续学习' : '开始学习'}
          </button>
        </aside>
      </div>
    </div>
  )
}
