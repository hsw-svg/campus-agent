export type TeacherAgentId =
  | 'learning_analysis'
  | 'classroom_interaction'
  | 'course_iteration'
  | 'grading'
  | 'teaching_report'

export interface TeacherAgentGroup {
  id: TeacherAgentId
  name: string
  shortName: string
  description: string
  agentIds: readonly string[]
  artifactTypes: readonly string[]
}

export const teacherAgentGroups: readonly TeacherAgentGroup[] = [
  {
    id: 'learning_analysis',
    name: '学情分析',
    shortName: '学情',
    description: '查看本学期多次班级整体分析与薄弱点变化。',
    agentIds: ['learning_analysis'],
    artifactTypes: ['learning_analysis'],
  },
  {
    id: 'classroom_interaction',
    name: '课堂互动',
    shortName: '互动',
    description: '汇总活动包、课堂观察和课后总结。',
    agentIds: ['classroom_interaction'],
    artifactTypes: ['classroom_activity_package', 'classroom_observation', 'classroom_summary'],
  },
  {
    id: 'course_iteration',
    name: '课程迭代',
    shortName: '迭代',
    description: '集中查看课程迭代、教案与题目生成记录。',
    agentIds: ['course_iteration', 'lesson_design'],
    artifactTypes: ['course_iteration', 'lesson_design', 'lesson_plan', 'question_set', 'quiz'],
  },
  {
    id: 'grading',
    name: '作业批改',
    shortName: '批改',
    description: '追踪作业批改任务、评分建议和常见错误。',
    agentIds: ['grading'],
    artifactTypes: ['grading', 'homework_grading', 'assignment_grading'],
  },
  {
    id: 'teaching_report',
    name: '教学报告',
    shortName: '报告',
    description: '查看阶段性教学总结与可导出的报告记录。',
    agentIds: ['teaching_report'],
    artifactTypes: ['teaching_report', 'teaching_summary'],
  },
] as const

export function agentGroupFor(value: string | null | undefined): TeacherAgentGroup | null {
  if (!value) return null
  return teacherAgentGroups.find((group) => group.id === value || group.agentIds.includes(value)) ?? null
}

export function agentGroupForArtifactType(type: string | null | undefined): TeacherAgentGroup | null {
  if (!type) return null
  return teacherAgentGroups.find((group) => group.artifactTypes.includes(type)) ?? null
}
