import {
  ArrowRight,
  BookOpenCheck,
  Check,
  CircleHelp,
  Compass,
  LockKeyhole,
  MessageCircleQuestion,
  NotebookPen,
  Orbit,
  Play,
  Route,
  Sparkles,
} from 'lucide-react'
import { motion, useReducedMotion } from 'motion/react'
import { useState, type CSSProperties } from 'react'
import type { CourseDetail, CourseSummary } from '../api'
import planetImage from '../assets/student-orbit/course-planet.webp'
import companionImage from '../assets/student-orbit/ai-companion.webp'
import CourseArtwork from './CourseArtwork'

interface StudentOrbitHomeProps {
  courses: CourseSummary[]
  learningCourse: CourseDetail | null
  learningChapterId: string | null
  loading: boolean
  onOpenCourses: () => void
  onStartCourse: (course: CourseSummary | CourseDetail, chapterId?: string) => void
  onOpenBook: () => void
  onOpenLearningSpace: () => void
  onAsk: (prompt: string) => void
}

const fallbackStages = ['课程导览', '核心概念', '知识问答', '随堂练习', '总结巩固']

const routeItems = [
  { label: '预习回顾', caption: '梳理已有知识', icon: Orbit },
  { label: '知识学习', caption: '阅读交互教材', icon: BookOpenCheck },
  { label: '随堂练习', caption: '检验当前理解', icon: NotebookPen },
  { label: 'AI 问答', caption: '追问关键难点', icon: MessageCircleQuestion },
  { label: '总结巩固', caption: '形成学习成果', icon: Check },
]

export default function StudentOrbitHome({
  courses,
  learningCourse,
  learningChapterId,
  loading,
  onOpenCourses,
  onStartCourse,
  onOpenBook,
  onOpenLearningSpace,
  onAsk,
}: StudentOrbitHomeProps) {
  const reduceMotion = useReducedMotion()
  const [companionOpen, setCompanionOpen] = useState(false)
  const featuredCourse = learningCourse ?? courses.find((course) => course.started) ?? courses[0] ?? null
  const currentChapter = learningCourse?.chapters.find((chapter) => chapter.id === learningChapterId)
    ?? learningCourse?.chapters.find((chapter) => chapter.current)
    ?? learningCourse?.chapters[0]
    ?? null
  const orbitStages = learningCourse?.chapters.slice(0, 7).map((chapter) => ({
    id: chapter.id,
    label: chapter.title,
    state: chapter.completed ? 'complete' : chapter.current ? 'active' : 'locked',
  })) ?? fallbackStages.map((label, index) => ({
    id: `stage-${index}`,
    label,
    state: index === 0 ? 'active' : 'locked',
  }))

  const startFeaturedCourse = () => {
    if (featuredCourse) onStartCourse(featuredCourse, currentChapter?.id)
    else onOpenCourses()
  }

  return (
    <section className="student-orbit-home" aria-label="星图学习舱">
      <aside className="student-orbit-courses" aria-label="我的课程与教材">
        <div className="student-orbit-section-heading">
          <div>
            <span>我的课程</span>
            <strong>{courses.length || '—'}</strong>
          </div>
          <button type="button" onClick={onOpenCourses}>全部课程<ArrowRight /></button>
        </div>

        <div className="student-orbit-course-list" aria-live="polite">
          {loading && courses.length === 0 && <div className="student-orbit-course-skeleton">正在装载课程星图…</div>}
          {!loading && courses.length === 0 && (
            <button type="button" className="student-orbit-empty-course" onClick={onOpenCourses}>
              <Compass />
              <span>从课程中心选择第一门课程</span>
            </button>
          )}
          {courses.slice(0, 3).map((course) => {
            const selected = featuredCourse?.id === course.id
            return (
              <button
                type="button"
                key={course.id}
                className="student-orbit-course-card"
                data-selected={selected}
                onClick={() => onStartCourse(course)}
                aria-pressed={selected}
              >
                <span className="student-orbit-course-art" aria-hidden="true"><CourseArtwork thumbnailKey={course.thumbnail_key} name={course.name} /></span>
                <span className="min-w-0">
                  <strong>{course.name}</strong>
                  <small>{course.category ?? '通识课程'} · {course.started ? `已学 ${course.progress_percent}%` : '尚未开始'}</small>
                </span>
                <Play aria-hidden="true" />
              </button>
            )
          })}
        </div>

        <div className="student-orbit-materials">
          <div className="student-orbit-section-heading">
            <div><span>交互教材</span></div>
            <button type="button" onClick={onOpenBook}>打开教材<ArrowRight /></button>
          </div>
          <button type="button" onClick={onOpenBook}>
            <BookOpenCheck />
            <span><strong>课程阅读舱</strong><small>教材、笔记与章节问答</small></span>
          </button>
          <button type="button" onClick={onOpenLearningSpace}>
            <Route />
            <span><strong>学习空间</strong><small>查看书籍与学习记录</small></span>
          </button>
        </div>
      </aside>

      <div className="student-orbit-stage">
        <div className="student-orbit-stage-copy">
          <span><Sparkles />当前课程星图</span>
          <h2>{featuredCourse?.name ?? '选择一门课程，开启学习航线'}</h2>
          <p>{currentChapter ? `当前章节：${currentChapter.title}` : '课程章节会围绕星球展开，完成状态和下一步清晰可见。'}</p>
        </div>

        <div className="student-orbit-system" aria-label="课程章节轨道">
          <motion.img
            className="student-orbit-planet"
            src={planetImage}
            alt="蓝色课程星球"
            animate={reduceMotion ? undefined : { y: [0, -7, 0] }}
            transition={reduceMotion ? undefined : { duration: 7, repeat: Infinity, ease: 'easeInOut' }}
          />
          <div className="student-orbit-ring student-orbit-ring-a" aria-hidden="true" />
          <div className="student-orbit-ring student-orbit-ring-b" aria-hidden="true" />
          <div className="student-orbit-ring student-orbit-ring-c" aria-hidden="true" />

          <div className="student-orbit-primary-card">
            <span>{currentChapter ? '继续上次内容' : featuredCourse ? '课程已就绪' : '等待选择课程'}</span>
            <strong>{currentChapter?.title ?? featuredCourse?.name ?? '课程中心'}</strong>
            <button type="button" onClick={startFeaturedCourse} disabled={loading}>
              {featuredCourse ? '继续学习' : '选择课程'}<ArrowRight />
            </button>
          </div>

          {orbitStages.map((stage, index) => (
            <button
              type="button"
              key={stage.id}
              className="student-orbit-node"
              data-state={stage.state}
              style={{ '--orbit-index': index, '--orbit-count': orbitStages.length } as CSSProperties}
              onClick={() => {
                if (learningCourse && stage.state !== 'locked') onStartCourse(learningCourse, stage.id)
              }}
              disabled={stage.state === 'locked'}
              aria-label={`${stage.label}，${stage.state === 'complete' ? '已完成' : stage.state === 'active' ? '当前章节' : '尚未解锁'}`}
            >
              <span>{stage.state === 'complete' ? <Check /> : stage.state === 'active' ? <Sparkles /> : <LockKeyhole />}</span>
              <small>{index + 1}</small>
              <strong>{stage.label}</strong>
            </button>
          ))}

          <button
            type="button"
            className="student-orbit-companion-toggle"
            aria-expanded={companionOpen}
            aria-controls="student-orbit-companion"
            onClick={() => setCompanionOpen((open) => !open)}
          >
            <Sparkles />AI 学伴
          </button>
        </div>
      </div>

      <aside id="student-orbit-companion" className="student-orbit-companion" data-open={companionOpen} aria-label="AI 学习伙伴">
        <button type="button" className="student-orbit-companion-close" onClick={() => setCompanionOpen(false)} aria-label="收起 AI 学习伙伴">收起</button>
        <div className="student-orbit-companion-visual">
          <span>AI 学习伙伴</span>
          <img src={companionImage} alt="智汇校园 AI 学习伙伴" />
        </div>
        <div className="student-orbit-companion-copy">
          <div><Sparkles /><span><strong>随时协助</strong><small>围绕当前课程提供解释与练习</small></span></div>
          <p>{currentChapter ? `正在关注「${currentChapter.title}」` : '选择课程后，我会跟随你的章节进度。'}</p>
        </div>
        <div className="student-orbit-questions">
          <button type="button" onClick={() => onAsk('请用一个具体例子解释当前章节的核心概念。')}><CircleHelp />举个例子解释核心概念</button>
          <button type="button" onClick={() => onAsk('请根据当前章节生成一道随堂练习，并在我回答后给出反馈。')}><NotebookPen />生成一道随堂练习</button>
          <button type="button" onClick={() => onAsk('请总结当前章节，并指出最容易混淆的知识点。')}><MessageCircleQuestion />梳理容易混淆的知识点</button>
        </div>
      </aside>

      <ol className="student-orbit-route" aria-label="今日学习航线">
        {routeItems.map(({ label, caption, icon: Icon }, index) => {
          const state = index === 0 ? '已完成' : index === 1 ? '当前' : '待开始'
          return (
          <li key={label} data-state={index === 0 ? 'complete' : index === 1 ? 'active' : 'future'} aria-current={index === 1 ? 'step' : undefined}>
            <span><Icon /></span>
            <div><strong>{label}</strong><small>{caption}</small><em className="sr-only">{state}</em></div>
          </li>
        )})}
      </ol>
    </section>
  )
}
