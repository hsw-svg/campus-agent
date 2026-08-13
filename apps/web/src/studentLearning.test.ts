import assert from 'node:assert/strict'
import test from 'node:test'
import type { Conversation, CourseDetail } from './api'
import {
  buildTutorRecommendedQuestions,
  firstCourseTextbookPage,
  latestStudentCourseConversation,
  normalizeStudentVisibleText,
  studentChatConversations,
  startedStudentCourses,
} from './studentLearning'

const course: CourseDetail = {
  id: 'course-linear-algebra',
  name: '线性代数',
  description: '矩阵与线性空间',
  teacher_name: null,
  starts_at: null,
  category: '数学基础',
  thumbnail_key: 'linear-algebra',
  created_at: '2026-08-12T08:00:00Z',
  updated_at: '2026-08-12T08:00:00Z',
  chapter_count: 1,
  completed_chapter_count: 0,
  started: true,
  progress_percent: 25,
  last_studied_at: '2026-08-12T08:00:00Z',
  deeptutor_book_id: 'bk-linear-algebra',
  chapters: [
    {
      id: 'chapter-matrix',
      title: '矩阵乘法',
      summary: '理解矩阵乘法的维度条件',
      position: 1,
      estimated_minutes: 30,
      knowledge_points: ['维度匹配', '线性变换'],
      deeptutor_chapter_id: 'ch-matrix',
      deeptutor_page_ids: ['pg-matrix'],
      completed: false,
      current: true,
    },
  ],
  current_chapter_id: 'chapter-matrix',
  weak_points: [],
}

function conversation(overrides: Partial<Conversation>): Conversation {
  return {
    id: 'conversation-default',
    title: '新对话',
    agent_id: null,
    course_id: null,
    chapter_id: null,
    created_at: '2026-08-12T08:00:00Z',
    updated_at: '2026-08-12T08:00:00Z',
    ...overrides,
  }
}

test('selects latest matching course conversation and excludes resume history', () => {
  const conversations = [
    conversation({
      id: 'older-matrix',
      course_id: course.id,
      chapter_id: 'chapter-matrix',
      updated_at: '2026-08-12T09:00:00Z',
    }),
    conversation({
      id: 'newer-matrix',
      course_id: course.id,
      chapter_id: 'chapter-matrix',
      updated_at: '2026-08-12T10:00:00Z',
    }),
    conversation({
      id: 'other-course',
      course_id: 'course-calculus',
      chapter_id: 'chapter-limit',
      updated_at: '2026-08-12T11:00:00Z',
    }),
    conversation({
      id: 'resume-run',
      agent_id: 'resume_helper',
      updated_at: '2026-08-12T12:00:00Z',
    }),
  ]

  assert.deepEqual(
    studentChatConversations(conversations).map((item) => item.id),
    ['other-course', 'newer-matrix', 'older-matrix'],
  )
  assert.equal(
    latestStudentCourseConversation(conversations, course.id, 'chapter-matrix')?.id,
    'newer-matrix',
  )
  assert.equal(latestStudentCourseConversation(conversations)?.id, 'other-course')
})

test('builds three contextual and role-specific recommended questions', () => {
  const chapter = course.chapters[0]
  const recommendations = (['default', 'peer', 'research-assistant', 'teacher'] as const)
    .map((role) => buildTutorRecommendedQuestions(role, course, chapter))

  for (const questions of recommendations) {
    assert.equal(questions.length, 3)
    assert.ok(questions.every((question) => question.label.includes('矩阵乘法') || question.prompt.includes('矩阵乘法')))
    assert.ok(questions.some((question) => question.prompt.includes('维度匹配')))
  }
  assert.equal(new Set(recommendations.map((items) => items[0].prompt)).size, 4)
})

test('falls back to role-aware generic questions without inventing a course', () => {
  const questions = buildTutorRecommendedQuestions('peer', null, null)

  assert.equal(questions.length, 3)
  assert.ok(questions.every((question) => !question.prompt.includes('线性代数')))
  assert.ok(questions.some((question) => question.prompt.includes('同学')))
})

test('normalizes legacy student-visible internal branding', () => {
  assert.equal(
    normalizeStudentVisibleText('DeepTutor助手发现：这里需要复习。'),
    'AI 学伴发现：这里需要复习。',
  )
  assert.equal(
    normalizeStudentVisibleText('deep tutor 建议先画图。'),
    '智汇校园 建议先画图。',
  )
})

test('keeps only started courses and orders recent learning first', () => {
  const notStarted = { ...course, id: 'course-new', started: false, last_studied_at: null }
  const recent = { ...course, id: 'course-recent', last_studied_at: '2026-08-12T12:00:00Z' }

  assert.deepEqual(
    startedStudentCourses([course, notStarted, recent]).map((item) => item.id),
    ['course-recent', course.id],
  )
})

test('resolves a bound Tutor page without inventing a link', () => {
  assert.deepEqual(firstCourseTextbookPage(course, course.chapters[0]), {
    bookId: 'bk-linear-algebra',
    pageId: 'pg-matrix',
  })
  assert.equal(firstCourseTextbookPage({ ...course, deeptutor_book_id: null }), null)
  assert.equal(firstCourseTextbookPage({
    ...course,
    chapters: [{ ...course.chapters[0], deeptutor_page_ids: [] }],
  }), null)
})
