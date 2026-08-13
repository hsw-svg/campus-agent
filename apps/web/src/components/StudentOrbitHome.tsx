import {
  ArrowLeft,
  ArrowRight,
  Bot,
  BookOpen,
  BookOpenCheck,
  Check,
  CircleHelp,
  Compass,
  GraduationCap,
  FileUp,
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
import { useMemo, useState, type CSSProperties, type ReactNode } from 'react'
import type { CourseDetail, CourseSummary } from '../api'
import { buildTutorRecommendedQuestions, firstCourseTextbookPage, type TutorRoleId } from '../studentLearning'
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
  onSelectCourse: (course: CourseSummary) => void | Promise<void>
  onSelectChapter: (course: CourseDetail, chapterId: string) => void | Promise<void>
  onBackToOverview: () => void
  onManageCourse: (course: CourseSummary | CourseDetail) => void | Promise<void>
  onOpenTextbook: (bookId: string, pageId: string) => void
  onOpenBook: () => void
  onOpenLearningSpace: () => void
  onAsk: (prompt: string) => void | Promise<void>
  selectedRoleId: TutorRoleId
  onSelectRole: (role: TutorRoleId) => void
  composer: ReactNode
  conversationActive: boolean
  conversationContent: ReactNode
  materialCount: number
  materialNotice: string | null
  onUploadMaterial: () => void
}

const questionIcons = [CircleHelp, NotebookPen, MessageCircleQuestion]

const tutorRoles = [
  { id: 'default', label: '默认学伴', description: '均衡讲解与学习引导', icon: Bot, image: defaultCompanionImage },
  { id: 'peer', label: '同伴学友', description: '平等交流，鼓励共同思考', icon: UsersRound, image: peerCompanionImage },
  { id: 'research-assistant', label: '研究助理', description: '重视证据、资料与推理', icon: Microscope, image: researchCompanionImage },
  { id: 'teacher', label: '导师', description: '结构化讲授与逐步检查', icon: GraduationCap, image: teacherCompanionImage },
] as const

export default function StudentOrbitHome({
  courses,
  learningCourse,
  learningChapterId,
  loading,
  onOpenCourses,
  onSelectCourse,
  onSelectChapter,
  onBackToOverview,
  onManageCourse,
  onOpenTextbook,
  onOpenBook,
  onOpenLearningSpace,
  onAsk,
  selectedRoleId,
  onSelectRole,
  composer,
  conversationActive,
  conversationContent,
  materialCount,
  materialNotice,
  onUploadMaterial,
}: StudentOrbitHomeProps) {
  const reduceMotion = useReducedMotion()
  const [companionOpen, setCompanionOpen] = useState(false)
  const [roleMenuOpen, setRoleMenuOpen] = useState(false)
  const selectedRole = tutorRoles.find((role) => role.id === selectedRoleId) ?? tutorRoles[0]
  const SelectedRoleIcon = selectedRole.icon
  const currentChapter = learningChapterId
    ? learningCourse?.chapters.find((chapter) => chapter.id === learningChapterId) ?? null
    : null
  const recommendedQuestions = useMemo(
    () => buildTutorRecommendedQuestions(selectedRoleId, learningCourse, currentChapter),
    [currentChapter, learningCourse, selectedRoleId],
  )
  const orbitStages = learningCourse?.chapters.map((chapter) => ({
    id: chapter.id,
    label: chapter.title,
    state: chapter.completed ? 'complete' : chapter.id === learningChapterId ? 'active' : 'available',
  })) ?? []
  const textbookEntry = firstCourseTextbookPage(learningCourse, currentChapter)

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
          {courses.map((course) => {
            const selected = learningCourse?.id === course.id
            return (
              <button
                type="button"
                key={course.id}
                className="student-orbit-course-card"
                data-selected={selected}
                onClick={() => { void onSelectCourse(course) }}
                aria-pressed={selected}
              >
                <span className="student-orbit-course-art" aria-hidden="true"><CourseArtwork thumbnailKey={course.thumbnail_key} name={course.name} /></span>
                <span className="min-w-0">
                  <strong>{course.name}</strong>
                  <small>{course.category ?? '通识课程'} · 已学 {course.progress_percent}%</small>
                </span>
                {selected ? <Check aria-hidden="true" /> : <Play aria-hidden="true" />}
              </button>
            )
          })}
        </div>

        <div className="student-orbit-materials">
          <div className="student-orbit-section-heading">
            <div><span>课程教材</span><strong>{materialCount || '—'}</strong></div>
            <button type="button" onClick={onOpenBook}>打开教材<ArrowRight /></button>
          </div>
          <button type="button" onClick={onUploadMaterial} disabled={!learningCourse}>
            <FileUp />
            <span>
              <strong>上传课程教材</strong>
              <small>{learningCourse ? `绑定到「${learningCourse.name}」` : '请先选择课程'}</small>
            </span>
          </button>
          {materialNotice && <p className="px-2 text-xs leading-5 text-teal-100" role="status">{materialNotice}</p>}
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
          <span><Sparkles />{learningCourse ? '课程章节星图' : '我的学习星系'}</span>
          <h2>{learningCourse?.name ?? '正在学习的课程围绕星球展开'}</h2>
          <p>{learningCourse ? (currentChapter ? `当前章节：${currentChapter.title}` : '选择一个章节，开始带上下文的学习与问答。') : `${courses.length} 门课程正在学习，点击课程查看真实章节与进度。`}</p>
        </div>

        <div className="student-orbit-system" aria-label={learningCourse ? '课程章节轨道' : '正在学习课程轨道'}>
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
            <span><Sparkles />{learningCourse ? '课程已定位' : '学习总览'}</span>
            <strong>{currentChapter?.title ?? learningCourse?.name ?? `${courses.length} 门课程学习中`}</strong>
          </div>

          {!learningCourse && courses.map((course, index) => (
            <button
              type="button"
              key={course.id}
              className="student-orbit-node student-orbit-course-node"
              data-state="course"
              style={{
                ...orbitPosition(index, courses.length),
                '--course-progress': `${Math.max(0, Math.min(100, course.progress_percent)) * 3.6}deg`,
              } as CSSProperties}
              onClick={() => { void onSelectCourse(course) }}
              aria-label={`${course.name}，学习进度 ${course.progress_percent}%`}
            >
              <span><BookOpen /></span>
              <small>{course.progress_percent}% 已完成</small>
              <strong>{course.name}</strong>
            </button>
          ))}

          {learningCourse && orbitStages.map((stage, index) => (
            <button
              type="button"
              key={stage.id}
              className="student-orbit-node"
              data-state={stage.state}
              style={orbitPosition(index, orbitStages.length)}
              onClick={() => { void onSelectChapter(learningCourse, stage.id) }}
              aria-current={stage.state === 'active' ? 'step' : undefined}
              aria-label={`${stage.label}，${stage.state === 'complete' ? '已完成' : stage.state === 'active' ? '当前章节' : '可学习'}`}
            >
              <span>{stage.state === 'complete' ? <Check /> : stage.state === 'active' ? <Sparkles /> : <Play />}</span>
              <small>第 {index + 1} 章</small>
              <strong>{stage.label}</strong>
            </button>
          ))}

          {!learningCourse && !loading && courses.length === 0 && (
            <button type="button" className="student-orbit-empty-state" onClick={onOpenCourses}><Compass /><strong>还没有正在学习的课程</strong><small>前往课程中心选择并开始学习</small></button>
          )}
          {learningCourse && learningCourse.chapters.length === 0 && (
            <button type="button" className="student-orbit-empty-state" onClick={() => { void onManageCourse(learningCourse) }}><BookOpenCheck /><strong>课程还没有章节</strong><small>创建交互教材后自动生成章节</small></button>
          )}

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
        {learningCourse && (
          <div className="student-orbit-stage-actions" aria-label="课程星图操作">
            <button type="button" onClick={onBackToOverview}><ArrowLeft />返回课程总览</button>
            <button type="button" onClick={() => { void onManageCourse(learningCourse) }}><Settings2 />管理课程与教材</button>
            {textbookEntry && <button type="button" data-primary="true" onClick={() => onOpenTextbook(textbookEntry.bookId, textbookEntry.pageId)}><BookOpenCheck />进入教材学习</button>}
          </div>
        )}
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
            <header><strong>选择学伴角色</strong><small>回答方式随角色动态调整</small></header>
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
          {recommendedQuestions.map((question, index) => {
            const QuestionIcon = questionIcons[index] ?? CircleHelp
            return (
              <button type="button" key={question.prompt} onClick={() => launchConversation(question.prompt)}>
                <QuestionIcon />{question.label}
              </button>
            )
          })}
        </div>
      </aside>

      <div className="student-orbit-composer-slot">{composer}</div>
    </section>
  )
}

function orbitPosition(index: number, count: number): CSSProperties {
  const safeCount = Math.max(count, 1)
  const angle = -Math.PI / 2 + (index * Math.PI * 2) / safeCount
  return {
    left: `${50 + Math.cos(angle) * 45}%`,
    top: `${50 + Math.sin(angle) * 39}%`,
  }
}
