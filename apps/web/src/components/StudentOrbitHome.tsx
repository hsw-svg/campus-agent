import {
  ArrowRight,
  Bot,
  BookOpenCheck,
  Check,
  CircleHelp,
  Compass,
  GraduationCap,
  LockKeyhole,
  MessageCircleQuestion,
  Microscope,
  NotebookPen,
  Play,
  Route,
  Settings2,
  Sparkles,
  UsersRound,
} from 'lucide-react'
import { motion, useReducedMotion } from 'motion/react'
import { useState, type CSSProperties, type ReactNode } from 'react'
import type { CourseDetail, CourseSummary } from '../api'
import planetImage from '../assets/student-orbit/course-planet.webp'
import defaultCompanionImage from '../assets/student-orbit/ai-companion-default.webp'
import peerCompanionImage from '../assets/student-orbit/ai-companion-peer.webp'
import researchCompanionImage from '../assets/student-orbit/ai-companion-research.webp'
import teacherCompanionImage from '../assets/student-orbit/ai-companion-teacher.webp'
import CourseArtwork from './CourseArtwork'

interface StudentOrbitHomeProps {
  courses: CourseSummary[]
  learningCourse: CourseDetail | null
  learningChapterId: string | null
  loading: boolean
  onOpenCourses: () => void
  onStartCourse: (course: CourseSummary | CourseDetail, chapterId?: string) => void | Promise<void>
  onOpenBook: () => void
  onOpenLearningSpace: () => void
  onAsk: (prompt: string) => void | Promise<void>
  selectedRoleId: TutorRoleId
  onSelectRole: (role: TutorRoleId) => void
  composer: ReactNode
  conversationActive: boolean
  conversationContent: ReactNode
}

const fallbackStages = ['课程导览', '核心概念', '知识问答', '随堂练习', '总结巩固']

const tutorRoles = [
  { id: 'default', label: '默认学伴', description: '均衡讲解与学习引导', icon: Bot, image: defaultCompanionImage },
  { id: 'peer', label: '同伴学友', description: '平等交流，鼓励共同思考', icon: UsersRound, image: peerCompanionImage },
  { id: 'research-assistant', label: '研究助理', description: '重视证据、资料与推理', icon: Microscope, image: researchCompanionImage },
  { id: 'teacher', label: '导师', description: '结构化讲授与逐步检查', icon: GraduationCap, image: teacherCompanionImage },
] as const

export type TutorRoleId = (typeof tutorRoles)[number]['id']

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
  selectedRoleId,
  onSelectRole,
  composer,
  conversationActive,
  conversationContent,
}: StudentOrbitHomeProps) {
  const reduceMotion = useReducedMotion()
  const [companionOpen, setCompanionOpen] = useState(false)
  const [roleMenuOpen, setRoleMenuOpen] = useState(false)
  const selectedRole = tutorRoles.find((role) => role.id === selectedRoleId) ?? tutorRoles[0]
  const SelectedRoleIcon = selectedRole.icon
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

  const launchConversation = (prompt: string) => {
    const cleanPrompt = prompt.trim()
    if (!cleanPrompt) return
    setRoleMenuOpen(false)
    void onAsk(cleanPrompt)
  }

  return (
    <section className="student-orbit-home" data-conversation={conversationActive} aria-label="星图学习舱">
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
                onClick={() => { void onStartCourse(course) }}
                aria-pressed={selected}
              >
                <span className="student-orbit-course-art" aria-hidden="true"><CourseArtwork thumbnailKey={course.thumbnail_key} name={course.name} /></span>
                <span className="min-w-0">
                  <strong>{course.name}</strong>
                  <small>{course.category ?? '通识课程'} · {course.started ? `已学 ${course.progress_percent}%` : '尚未开始'}</small>
                </span>
                {selected ? <Check aria-hidden="true" /> : <Play aria-hidden="true" />}
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
            <span><Sparkles />{featuredCourse ? '课程已就绪' : '等待选择课程'}</span>
            <strong>{currentChapter?.title ?? featuredCourse?.name ?? '前往课程中心选择课程'}</strong>
          </div>

          {orbitStages.map((stage, index) => (
            <button
              type="button"
              key={stage.id}
              className="student-orbit-node"
              data-state={stage.state}
              style={{ '--orbit-index': index, '--orbit-count': orbitStages.length } as CSSProperties}
              onClick={() => {
                if (learningCourse && stage.state !== 'locked') void onStartCourse(learningCourse, stage.id)
              }}
              disabled={stage.state === 'locked'}
              aria-current={stage.state === 'active' ? 'step' : undefined}
              aria-label={`${stage.label}，${stage.state === 'complete' ? '已完成' : stage.state === 'active' ? '当前章节' : '尚未解锁'}`}
            >
              <span>{stage.state === 'complete' ? <Check /> : stage.state === 'active' ? <Sparkles /> : <LockKeyhole />}</span>
              <small>第 {index + 1} 章</small>
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
        {conversationActive && <div className="student-orbit-conversation">{conversationContent}</div>}
      </div>

      <aside id="student-orbit-companion" className="student-orbit-companion" data-open={companionOpen} data-role={selectedRoleId} aria-label="AI 学习伙伴">
        <button type="button" className="student-orbit-companion-close" onClick={() => setCompanionOpen(false)} aria-label="收起 AI 学习伙伴">收起</button>
        <div className="student-orbit-companion-visual">
          <span>{selectedRole.label}</span>
          <button
            type="button"
            className="student-orbit-role-settings"
            aria-expanded={roleMenuOpen}
            aria-controls="student-orbit-role-menu"
            onClick={() => setRoleMenuOpen((open) => !open)}
          >
            <Settings2 /><span className="sr-only">设置 AI 学伴角色</span>
          </button>
          <img src={selectedRole.image} alt={`${selectedRole.label}机器人`} />
          <span className="student-orbit-role-badge"><SelectedRoleIcon /></span>
        </div>
        {roleMenuOpen && (
          <div id="student-orbit-role-menu" className="student-orbit-role-menu" role="menu" aria-label="选择 AI 学伴角色">
            <header><strong>选择学伴角色</strong><small>采用 DeepTutor 角色模式</small></header>
            {tutorRoles.map(({ id, label, description, icon: RoleIcon, image }) => (
              <button
                type="button"
                key={id}
                role="menuitemradio"
                aria-checked={selectedRoleId === id}
                data-selected={selectedRoleId === id}
                data-role={id}
                onClick={() => { onSelectRole(id); setRoleMenuOpen(false) }}
              >
                <span className="student-orbit-role-avatar"><img src={image} alt="" /><RoleIcon /></span>
                <span><strong>{label}</strong><small>{description}</small></span>
                {selectedRoleId === id && <Check aria-hidden="true" />}
              </button>
            ))}
          </div>
        )}
        <div className="student-orbit-companion-copy">
          <div><SelectedRoleIcon /><span><strong>{selectedRole.label}</strong><small>{selectedRole.description}</small></span></div>
          <p>{currentChapter ? `正在关注「${currentChapter.title}」` : '选择课程后，我会跟随你的章节进度。'}</p>
        </div>
        <div className="student-orbit-questions">
          <button type="button" onClick={() => launchConversation('请解释当前课程的核心知识点。')}><CircleHelp />解释课程核心知识点</button>
          <button type="button" onClick={() => launchConversation('请根据当前章节生成一道随堂练习，并在我回答后给出反馈。')}><NotebookPen />生成一道随堂练习</button>
          <button type="button" onClick={() => launchConversation('请总结当前章节，并指出最容易混淆的知识点。')}><MessageCircleQuestion />梳理容易混淆的知识点</button>
        </div>
      </aside>

      <div className="student-orbit-composer-slot">{composer}</div>
    </section>
  )
}
