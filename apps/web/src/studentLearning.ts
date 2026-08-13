import type { Conversation, CourseChapter, CourseDetail, CourseSummary } from './api'

export type TutorRoleId = 'default' | 'peer' | 'research-assistant' | 'teacher'

export interface TutorRecommendedQuestion {
  label: string
  prompt: string
}

export function startedStudentCourses(courses: CourseSummary[]): CourseSummary[] {
  return courses
    .filter((course) => course.started)
    .slice()
    .sort((left, right) => (
      (right.last_studied_at ?? '').localeCompare(left.last_studied_at ?? '')
      || left.name.localeCompare(right.name, 'zh-CN')
    ))
}

export function firstCourseTextbookPage(
  course: CourseDetail | null,
  chapter?: CourseChapter | null,
): { bookId: string; pageId: string } | null {
  if (!course?.deeptutor_book_id) return null
  const target = chapter ?? course.chapters.find((item) => item.deeptutor_page_ids.length > 0)
  const pageId = target?.deeptutor_page_ids[0]
  return pageId ? { bookId: course.deeptutor_book_id, pageId } : null
}

const INTERNAL_BRAND_PATTERN = /deep\s*tutor(?:助手|助教)?/gi

export function normalizeStudentVisibleText(content: string): string {
  return content.replace(INTERNAL_BRAND_PATTERN, (match) => (
    /(?:助手|助教)$/i.test(match) ? 'AI 学伴' : '智汇校园'
  ))
}

export function studentChatConversations(conversations: Conversation[]): Conversation[] {
  return conversations
    .filter((conversation) => conversation.agent_id !== 'resume_helper')
    .slice()
    .sort((left, right) => right.updated_at.localeCompare(left.updated_at))
}

export function latestStudentCourseConversation(
  conversations: Conversation[],
  courseId?: string,
  chapterId?: string | null,
): Conversation | null {
  return studentChatConversations(conversations).find((conversation) => {
    if (conversation.course_id === null) return false
    if (courseId !== undefined && conversation.course_id !== courseId) return false
    if (chapterId !== undefined && conversation.chapter_id !== chapterId) return false
    return true
  }) ?? null
}

function contextualSubject(
  course: CourseSummary | CourseDetail | null,
  chapter: CourseChapter | null,
): { subject: string; knowledgePoint: string | null } {
  if (course && chapter) {
    return {
      subject: `《${course.name}》的“${chapter.title}”`,
      knowledgePoint: chapter.knowledge_points[0] ?? null,
    }
  }
  if (course) return { subject: `《${course.name}》`, knowledgePoint: null }
  return { subject: '当前学习内容', knowledgePoint: null }
}

export function buildTutorRecommendedQuestions(
  role: TutorRoleId,
  course: CourseSummary | CourseDetail | null,
  chapter: CourseChapter | null,
): TutorRecommendedQuestion[] {
  const { subject, knowledgePoint } = contextualSubject(course, chapter)
  const focus = knowledgePoint ? `，重点说明“${knowledgePoint}”` : ''

  switch (role) {
    case 'peer':
      return [
        { label: `一起讨论${chapter?.title ?? '学习内容'}`, prompt: `请像同学一样和我讨论${subject}${focus}，先问问我的理解再补充。` },
        { label: `用类比理解${chapter?.title ?? '难点'}`, prompt: `请和我一起为${subject}找一个生活化类比${focus}，并讨论类比的局限。` },
        { label: `互相出题检查掌握`, prompt: `请围绕${subject}${focus}，像同学互测一样先出一道题，等我回答后再交流思路。` },
      ]
    case 'research-assistant':
      return [
        { label: `分析${chapter?.title ?? '核心问题'}`, prompt: `请分析${subject}的核心概念、关键假设和推理链${focus}。` },
        { label: `核对证据与边界`, prompt: `请梳理${subject}中哪些是事实、哪些是推断${focus}，并说明适用边界。` },
        { label: `提出可验证问题`, prompt: `请基于${subject}${focus}提出三个可以继续检索或验证的研究问题。` },
      ]
    case 'teacher':
      return [
        { label: `讲解${chapter?.title ?? '学习目标'}`, prompt: `请像导师一样讲解${subject}：先说明学习目标，再分层解释${focus}。` },
        { label: `示范典型例题`, prompt: `请围绕${subject}${focus}示范一道典型例题，并逐步说明每一步。` },
        { label: `检查是否真正掌握`, prompt: `请针对${subject}${focus}设计三个由浅入深的检查问题，逐题等待我回答。` },
      ]
    case 'default':
      return [
        { label: `解释${chapter?.title ?? '核心知识点'}`, prompt: `请清晰解释${subject}的核心知识点${focus}，并给一个简短例子。` },
        { label: `生成${chapter?.title ?? '随堂'}练习`, prompt: `请根据${subject}${focus}生成一道随堂练习，并在我回答后给出反馈。` },
        { label: `梳理${chapter?.title ?? '易混淆点'}`, prompt: `请总结${subject}${focus}，并指出最容易混淆的知识点和下一步建议。` },
      ]
  }
}
