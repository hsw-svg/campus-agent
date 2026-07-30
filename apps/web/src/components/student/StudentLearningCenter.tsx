/**
 * StudentLearningCenter — 课程卡片列表，点击"学习中心"后覆盖整个内容区。
 * 仅供学生端使用，放在 components/student/ 以避免与教师/行政端产生合并冲突。
 */

import { useEffect, useState, type ReactNode } from 'react'
import { motion } from 'motion/react'
import {
  BookOpen,
  Compass,
  ChevronRight,
  Loader,
  AlertCircle,
  GraduationCap,
  Search,
  Sparkles,
  FileText,
  HelpCircle,
  ClipboardList,
} from 'lucide-react'
import { listStudentCourses, type StudentCourse } from '../../studentApi'

interface StudentLearningCenterProps {
  token: string | null
  /** Called when the student picks a course to start a chat about it. */
  onStartChat: (prompt: string) => void
  /** Called when student clicks "新建学习任务" to open a blank chat. */
  onNewTask: () => void
}

const SUBJECT_ICONS: Record<string, ReactNode> = {
  default: <BookOpen className="w-6 h-6" />,
}

function subjectIcon(name: string): ReactNode {
  const lower = name.toLowerCase()
  if (lower.includes('数学') || lower.includes('math')) return <GraduationCap className="w-6 h-6" />
  if (lower.includes('英语') || lower.includes('english')) return <FileText className="w-6 h-6" />
  if (lower.includes('python') || lower.includes('编程') || lower.includes('计算机')) return <Sparkles className="w-6 h-6" />
  return SUBJECT_ICONS.default
}

const QUICK_ACTIONS = [
  {
    label: '论文大纲辅助',
    icon: <FileText className="w-5 h-5" />,
    prompt: '论文辅助：生成计算机大模型相关大纲',
  },
  {
    label: '知识概念答疑',
    icon: <HelpCircle className="w-5 h-5" />,
    prompt: '知识问答：Python 列表与元组的深度区别',
  },
  {
    label: '期末复习冲刺',
    icon: <ClipboardList className="w-5 h-5" />,
    prompt: '课程总结：自动生成 Python 复习备考冲刺计划',
  },
]

export default function StudentLearningCenter({
  token,
  onStartChat,
  onNewTask,
}: StudentLearningCenterProps) {
  const [courses, setCourses] = useState<StudentCourse[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    if (!token) return
    setLoading(true)
    setError(null)
    listStudentCourses(token)
      .then(setCourses)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : '课程加载失败'))
      .finally(() => setLoading(false))
  }, [token])

  const filtered = courses.filter(
    (c) =>
      !searchQuery ||
      c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (c.description ?? '').toLowerCase().includes(searchQuery.toLowerCase()),
  )

  return (
    <div className="flex-1 overflow-y-auto bg-background">
      {/* Hero bar */}
      <div className="bg-surface border-b border-outline-variant px-8 py-6">
        <div className="max-w-5xl mx-auto">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h2 className="font-display text-2xl font-bold text-on-surface">学习中心</h2>
              <p className="text-sm text-on-surface-variant mt-0.5">选择课程，开启智能辅导</p>
            </div>
            <button
              onClick={onNewTask}
              className="flex items-center gap-2 px-5 py-2.5 bg-secondary text-on-secondary rounded-xl font-semibold text-sm hover:opacity-95 active:scale-95 transition-all shadow-sm cursor-pointer shrink-0"
            >
              <Compass className="w-4 h-4" />
              新建学习任务
            </button>
          </div>

          {/* Search */}
          <div className="mt-4 relative max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-outline pointer-events-none" />
            <input
              type="text"
              placeholder="搜索课程…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 rounded-xl bg-surface-container border border-outline-variant text-sm outline-none focus:border-secondary transition-colors"
            />
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-8 py-8 space-y-10">
        {/* Quick actions */}
        <section>
          <h3 className="text-xs font-bold text-on-surface-variant uppercase tracking-wider mb-4">
            快捷入口
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {QUICK_ACTIONS.map((action) => (
              <button
                key={action.label}
                onClick={() => onStartChat(action.prompt)}
                className="flex items-center gap-3 p-4 bg-surface-container-lowest border border-outline-variant/60 rounded-2xl hover:border-secondary hover:shadow-md transition-all group cursor-pointer text-left"
              >
                <div className="w-10 h-10 rounded-xl bg-secondary-container/30 text-secondary flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
                  {action.icon}
                </div>
                <span className="font-semibold text-sm text-on-surface">{action.label}</span>
                <ChevronRight className="w-4 h-4 text-outline ml-auto opacity-0 group-hover:opacity-100 transition-opacity" />
              </button>
            ))}
          </div>
        </section>

        {/* Course list */}
        <section>
          <h3 className="text-xs font-bold text-on-surface-variant uppercase tracking-wider mb-4">
            我的课程
          </h3>

          {loading && (
            <div className="flex items-center justify-center py-16 gap-2 text-on-surface-variant">
              <Loader className="w-5 h-5 animate-spin" />
              <span className="text-sm">加载课程中…</span>
            </div>
          )}

          {!loading && error && (
            <div className="flex items-center gap-2 p-4 bg-error-container/30 rounded-2xl text-on-error-container text-sm">
              <AlertCircle className="w-5 h-5 shrink-0" />
              {error}
            </div>
          )}

          {!loading && !error && filtered.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 text-center space-y-3">
              <BookOpen className="w-12 h-12 text-outline/30" />
              <p className="text-sm font-semibold text-on-surface-variant">
                {searchQuery ? '没有找到匹配的课程' : '暂无可用课程'}
              </p>
              <button
                onClick={onNewTask}
                className="text-xs text-secondary font-bold hover:underline cursor-pointer"
              >
                直接开始学习 →
              </button>
            </div>
          )}

          {!loading && filtered.length > 0 && (
            <motion.div
              className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"
              initial="hidden"
              animate="visible"
              variants={{
                visible: { transition: { staggerChildren: 0.05 } },
                hidden: {},
              }}
            >
              {filtered.map((course) => (
                <motion.button
                  key={course.id}
                  variants={{
                    hidden: { opacity: 0, y: 16 },
                    visible: { opacity: 1, y: 0 },
                  }}
                  onClick={() => onStartChat(`课程资料问答：关于《${course.name}》的问题`)}
                  className="group flex flex-col gap-3 p-5 bg-surface-container-lowest border border-outline-variant/60 rounded-2xl hover:border-secondary hover:shadow-lg transition-all text-left cursor-pointer"
                >
                  <div className="flex items-start justify-between">
                    <div className="w-11 h-11 rounded-xl bg-secondary-container/30 text-secondary flex items-center justify-center shrink-0 group-hover:scale-105 group-hover:bg-secondary/10 transition-all">
                      {subjectIcon(course.name)}
                    </div>
                    <ChevronRight className="w-4 h-4 text-outline opacity-0 group-hover:opacity-100 transition-opacity mt-1" />
                  </div>

                  <div className="flex-1 min-w-0">
                    <p className="font-bold text-sm text-on-surface line-clamp-2 leading-snug">
                      {course.name}
                    </p>
                    {course.description && (
                      <p className="mt-1 text-xs text-on-surface-variant line-clamp-2 leading-relaxed">
                        {course.description}
                      </p>
                    )}
                  </div>

                  <div className="flex items-center gap-2 pt-1 border-t border-outline-variant/40">
                    <span className="text-[10px] text-secondary font-semibold">开始学习</span>
                    <span className="text-[10px] text-outline ml-auto">
                      {new Date(course.updated_at).toLocaleDateString('zh-CN', {
                        month: 'short',
                        day: 'numeric',
                      })}
                    </span>
                  </div>
                </motion.button>
              ))}
            </motion.div>
          )}
        </section>
      </div>
    </div>
  )
}
