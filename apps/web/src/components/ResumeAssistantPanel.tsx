import {
  AlertCircle,
  ArrowRight,
  BookOpenCheck,
  BriefcaseBusiness,
  Check,
  CheckCircle2,
  ClipboardCopy,
  FileCheck2,
  FileSearch,
  FileText,
  LoaderCircle,
  MessageSquareMore,
  RotateCcw,
  Sparkles,
  Upload,
} from 'lucide-react'
import { motion } from 'motion/react'
import { useMemo, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { ResumeAnalysisReport, ResumeIssueSeverity } from '../api'
import { useResumeAssistant } from '../hooks/useResumeAssistant'
import ResumeAgentHistoryPanel from './ResumeAgentHistoryPanel'

interface ResumeAssistantPanelProps {
  token: string | null
}

export default function ResumeAssistantPanel({ token }: ResumeAssistantPanelProps) {
  const assistant = useResumeAssistant(token)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const report = assistant.activeHistory?.artifact?.data.report ?? null
  const [copiedKey, setCopiedKey] = useState<string | null>(null)
  const draftMarkdown = useMemo(
    () => report?.optimized_resume_sections
      .map((section) => `## ${section.heading}\n\n${section.markdown}`)
      .join('\n\n') ?? '',
    [report],
  )

  const copyText = async (key: string, value: string) => {
    await navigator.clipboard.writeText(value)
    setCopiedKey(key)
    window.setTimeout(() => setCopiedKey((current) => current === key ? null : current), 1800)
  }

  return (
    <div className="student-resume-shell grid min-h-full w-full gap-4 xl:grid-cols-[minmax(0,1fr)_320px] xl:gap-0">
      <div className="min-w-0 space-y-5 p-1 sm:p-3 xl:overflow-y-auto xl:p-6">
        <section className="student-resume-hero relative overflow-hidden rounded-3xl border border-secondary/20 p-5 sm:p-7">
          <div className="absolute -right-10 -top-12 h-40 w-40 rounded-full bg-secondary/15 blur-2xl" />
          <div className="relative flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="max-w-2xl">
              <div className="inline-flex items-center gap-1.5 rounded-full border border-secondary/30 bg-secondary/10 px-3 py-1 text-[10px] font-black uppercase tracking-[0.16em] text-secondary">
                <Sparkles className="h-3.5 w-3.5" />AI Career Companion
              </div>
              <h1 className="mt-3 font-display text-2xl font-extrabold tracking-tight text-on-surface sm:text-3xl">简历助手</h1>
              <p className="mt-2 text-sm font-medium leading-relaxed text-on-surface-variant">基于你的真实简历与课程学习进度，定位表达问题、匹配岗位关键词，并生成有证据边界的优化草稿。</p>
            </div>
            <div className="flex shrink-0 items-center gap-3 rounded-2xl border border-outline-variant/80 bg-surface-container-lowest/80 p-3 backdrop-blur">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-secondary text-on-secondary"><FileSearch className="h-5 w-5" /></div>
              <div>
                <p className="text-[10px] font-bold text-outline">分析原则</p>
                <p className="text-xs font-black text-on-surface">真实证据 · 不虚构经历</p>
              </div>
            </div>
          </div>
        </section>

        {assistant.error && (
          <div role="alert" className="flex items-start gap-2 rounded-2xl border border-error/25 bg-error-container/80 px-4 py-3 text-xs font-semibold text-on-error-container">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />{assistant.error}
          </div>
        )}

        <section className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="student-resume-card rounded-3xl border border-outline-variant/70 bg-surface-container-lowest p-5">
            <SectionTitle index="01" title="上传当前简历" subtitle="支持 PDF、DOCX、TXT、Markdown，最大 25 MB" />
            <button
              type="button"
              disabled={assistant.uploading}
              onClick={() => fileInputRef.current?.click()}
              className="mt-4 flex w-full flex-col items-center justify-center rounded-2xl border-2 border-dashed border-secondary/25 bg-secondary/5 px-5 py-7 text-center transition-colors hover:border-secondary/50 hover:bg-secondary/10 disabled:cursor-wait disabled:opacity-60"
            >
              {assistant.uploading ? <LoaderCircle className="h-8 w-8 animate-spin text-secondary" /> : <Upload className="h-8 w-8 text-secondary" />}
              <span className="mt-2 text-sm font-black text-on-surface">{assistant.uploading ? '正在解析简历' : assistant.currentResume ? '上传新简历并替换当前版本' : '选择简历文件'}</span>
              <span className="mt-1 text-[10px] font-semibold text-outline">上传后不会自动调用 AI</span>
            </button>
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              accept=".pdf,.docx,.txt,.md"
              onChange={(event) => {
                const file = event.target.files?.[0]
                if (file) void assistant.uploadResume(file)
                event.currentTarget.value = ''
              }}
            />
            {assistant.currentResume && (
              <div className="mt-4 flex items-start gap-3 rounded-2xl border border-outline-variant/70 bg-surface-container-low p-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-secondary/10 text-secondary">
                  <FileCheck2 className="h-4.5 w-4.5" />
                </div>
                <div className="min-w-0">
                  <p className="text-[9px] font-black uppercase tracking-wider text-secondary">当前简历</p>
                  <p className="truncate text-xs font-black text-on-surface">{assistant.currentResume.filename}</p>
                  <p className="mt-0.5 text-[10px] font-semibold text-on-surface-variant">已提取 {assistant.currentResume.extracted_chars.toLocaleString()} 个字符</p>
                </div>
              </div>
            )}
            {assistant.uploadResult && assistant.uploadResult.id !== assistant.currentResume?.id && (
              <div className="mt-3 flex items-start gap-3 rounded-2xl border border-error/25 bg-error-container/60 p-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-error/10 text-error"><AlertCircle className="h-4.5 w-4.5" /></div>
                <div className="min-w-0">
                  <p className="text-[9px] font-black uppercase tracking-wider text-error">未替换当前简历</p>
                  <p className="truncate text-xs font-black text-on-surface">{assistant.uploadResult.filename}</p>
                  <p className="mt-0.5 text-[10px] font-semibold text-on-error-container">{assistant.uploadResult.status_message || '未提取到可读文本，请更换文件。'}</p>
                </div>
              </div>
            )}
          </div>

          <div className="student-resume-card rounded-3xl border border-outline-variant/70 bg-surface-container-lowest p-5">
            <SectionTitle index="02" title="设置求职方向" subtitle="均为可选；留空时生成通用优化建议" />
            <label className="mt-4 block">
              <span className="text-[11px] font-black text-on-surface">目标岗位</span>
              <div className="mt-1.5 flex items-center gap-2 rounded-xl border border-outline-variant bg-surface-container-lowest px-3 focus-within:border-secondary">
                <BriefcaseBusiness className="h-4 w-4 text-outline" />
                <input
                  value={assistant.targetRole}
                  onChange={(event) => assistant.setTargetRole(event.target.value)}
                  maxLength={160}
                  placeholder="例如：产品助理、Java 开发工程师"
                  className="min-w-0 flex-1 bg-transparent py-3 text-xs font-semibold text-on-surface outline-none placeholder:text-outline"
                />
              </div>
            </label>
            <label className="mt-3 block">
              <span className="text-[11px] font-black text-on-surface">职位描述（JD）</span>
              <textarea
                value={assistant.jobDescription}
                onChange={(event) => assistant.setJobDescription(event.target.value)}
                maxLength={12000}
                rows={5}
                placeholder="粘贴岗位职责与任职要求，用于关键词匹配和能力差距分析。"
                className="mt-1.5 w-full resize-y rounded-xl border border-outline-variant bg-surface-container-lowest px-3 py-3 text-xs font-semibold leading-relaxed text-on-surface outline-none placeholder:text-outline focus:border-secondary"
              />
            </label>
          </div>
        </section>

        <section className="student-resume-card rounded-3xl border border-outline-variant/70 bg-surface-container-lowest p-5">
          <SectionTitle index="03" title="选择课程学习证据" subtitle="已开始课程默认选中；未开始课程不会作为能力依据" />
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {assistant.loading ? (
              <div className="col-span-full flex items-center justify-center gap-2 py-8 text-xs font-bold text-outline"><LoaderCircle className="h-4 w-4 animate-spin" />加载真实课程进度</div>
            ) : assistant.courses.map((course) => {
              const selected = assistant.selectedCourseIds.includes(course.id)
              return (
                <button
                  key={course.id}
                  type="button"
                  disabled={!course.started}
                  aria-pressed={selected}
                  onClick={() => assistant.toggleCourse(course)}
                  className={`flex items-center gap-3 rounded-2xl border p-3 text-left transition-all ${selected ? 'border-secondary/35 bg-secondary/5 shadow-sm' : 'border-outline-variant/70 bg-surface-container-lowest'} disabled:cursor-not-allowed disabled:opacity-55`}
                >
                  <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${selected ? 'bg-secondary text-white' : 'bg-surface-container text-outline'}`}>
                    {selected ? <Check className="h-4 w-4" /> : <BookOpenCheck className="h-4 w-4" />}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-xs font-black text-on-surface">{course.name}</span>
                    <span className="mt-0.5 block text-[10px] font-semibold text-on-surface-variant">{course.started ? `已完成 ${course.completed_chapter_count}/${course.chapter_count} 章 · ${course.progress_percent}%` : '尚未开始 · 不可作为证据'}</span>
                  </span>
                </button>
              )
            })}
          </div>
        </section>

        <section className="flex flex-col gap-3 rounded-3xl border border-secondary/20 bg-secondary-container/25 p-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-black text-on-surface">准备好后，由你主动开始分析</p>
            <p className="mt-1 text-[11px] font-semibold text-on-surface-variant">{assistant.selectedCourseIds.length > 0 ? `本次将使用 ${assistant.selectedCourseIds.length} 门已开始课程作为辅助证据` : '本次不使用课程记录，将进行通用简历分析'}</p>
            {assistant.toolStatus && <p className="mt-1 text-[10px] font-bold text-secondary">{assistant.toolStatus}</p>}
          </div>
          <div className="flex shrink-0 gap-2">
            {assistant.status === 'failed' && (
              <button type="button" onClick={assistant.retryAnalysis} className="inline-flex items-center gap-1.5 rounded-xl border border-secondary/30 bg-surface-container-lowest px-4 py-2.5 text-xs font-black text-secondary">
                <RotateCcw className="h-4 w-4" />重新分析
              </button>
            )}
            <button
              type="button"
              disabled={!assistant.currentResume || assistant.status === 'running'}
              onClick={() => assistant.status === 'running' ? assistant.stopAnalysis() : void assistant.runAnalysis()}
              className="inline-flex items-center gap-2 rounded-xl bg-secondary px-5 py-2.5 text-xs font-black text-on-secondary shadow-[0_8px_20px_rgba(6,182,212,0.22)] transition-transform active:scale-95 disabled:cursor-not-allowed disabled:opacity-45"
            >
              {assistant.status === 'running' ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              {assistant.status === 'running' ? '分析中' : assistant.history.length > 0 ? '开始新的分析' : '开始分析'}
              {assistant.status !== 'running' && <ArrowRight className="h-4 w-4" />}
            </button>
          </div>
        </section>

        {assistant.activeHistory && !report && (
          <section className="student-resume-card rounded-3xl border border-outline-variant/70 bg-surface-container-lowest p-6 text-center">
            <AlertCircle className="mx-auto h-7 w-7 text-error" />
            <h2 className="mt-2 text-sm font-black text-on-surface">这次分析未生成报告</h2>
            <p className="mt-1 text-xs text-on-surface-variant">{assistant.activeHistory.error_message || '可以保留当前简历和设置后重新分析。'}</p>
          </section>
        )}

        {report && (
          <ResumeReportView
            report={report}
            draftMarkdown={draftMarkdown}
            copiedKey={copiedKey}
            onCopy={copyText}
          />
        )}

        {!report && !assistant.activeHistory && !assistant.loading && (
          <section className="student-resume-empty rounded-3xl border border-dashed border-outline-variant bg-surface-container-lowest/60 px-6 py-12 text-center">
            <FileText className="mx-auto h-8 w-8 text-outline" />
            <h2 className="mt-3 text-sm font-black text-on-surface">完整优化报告将在这里展示</h2>
            <p className="mt-1 text-xs font-medium text-on-surface-variant">包含问题清单、岗位匹配、课程能力映射和可复制的完整草稿。</p>
          </section>
        )}

        <section className="flex items-center justify-between gap-4 rounded-3xl border border-dashed border-primary/25 bg-primary/5 p-5">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary"><MessageSquareMore className="h-5 w-5" /></div>
            <div>
              <p className="text-sm font-black text-on-surface">模拟面试</p>
              <p className="mt-0.5 text-[11px] font-semibold text-on-surface-variant">根据简历和目标岗位生成追问与反馈</p>
            </div>
          </div>
          <span className="shrink-0 rounded-full bg-primary/10 px-3 py-1.5 text-[10px] font-black text-primary">即将上线</span>
        </section>
      </div>

      <ResumeAgentHistoryPanel
        history={assistant.history}
        activeRunId={assistant.activeRunId}
        running={assistant.status === 'running'}
        onOpen={assistant.openHistory}
        onDelete={(runId) => { void assistant.removeHistory(runId) }}
      />
    </div>
  )
}

function SectionTitle({ index, title, subtitle }: { index: string; title: string; subtitle: string }) {
  return (
    <div className="flex items-start gap-3">
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-secondary/10 text-[10px] font-black text-secondary">{index}</span>
      <div>
        <h2 className="text-sm font-black text-on-surface">{title}</h2>
        <p className="mt-0.5 text-[10px] font-semibold text-on-surface-variant">{subtitle}</p>
      </div>
    </div>
  )
}

function ResumeReportView({
  report,
  draftMarkdown,
  copiedKey,
  onCopy,
}: {
  report: ResumeAnalysisReport
  draftMarkdown: string
  copiedKey: string | null
  onCopy: (key: string, value: string) => Promise<void>
}) {
  return (
    <motion.section initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="student-resume-card space-y-5 rounded-3xl border border-outline-variant/70 bg-surface-container-lowest p-5 sm:p-7">
      <div className="flex items-start gap-3">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-secondary text-white"><CheckCircle2 className="h-5 w-5" /></div>
        <div>
          <p className="text-[10px] font-black uppercase tracking-[0.16em] text-secondary">Resume Analysis</p>
          <h2 className="mt-0.5 text-xl font-black text-on-surface">简历优化报告</h2>
          <p className="mt-2 text-sm font-medium leading-relaxed text-on-surface-variant">{report.overall_summary}</p>
        </div>
      </div>

      <div>
        <ReportHeading title="问题清单" count={report.issues.length} />
        <div className="mt-3 grid gap-3">
          {report.issues.map((issue, index) => (
            <div key={`${issue.section}-${index}`} className="rounded-2xl border border-outline-variant/70 bg-surface-container-low p-4">
              <div className="flex items-center gap-2">
                <span className={`rounded-full px-2 py-1 text-[9px] font-black ${severityClass(issue.severity)}`}>{severityLabel(issue.severity)}</span>
                <p className="text-xs font-black text-on-surface">{issue.section}</p>
              </div>
              <p className="mt-2 text-xs font-semibold leading-relaxed text-on-surface">{issue.problem}</p>
              <p className="mt-2 text-[10px] leading-relaxed text-on-surface-variant"><strong>依据：</strong>{issue.evidence}</p>
              <p className="mt-1 text-[10px] leading-relaxed text-secondary"><strong>建议：</strong>{issue.suggestion}</p>
            </div>
          ))}
        </div>
      </div>

      <div>
        <ReportHeading title="分模块修改建议" count={report.section_suggestions.length} />
        <div className="mt-3 grid gap-3 lg:grid-cols-2">
          {report.section_suggestions.map((section) => (
            <div key={section.section} className="rounded-2xl border border-outline-variant/70 p-4">
              <h3 className="text-xs font-black text-on-surface">{section.section}</h3>
              <ul className="mt-2 space-y-1 text-[11px] leading-relaxed text-on-surface-variant">
                {section.suggestions.map((item) => <li key={item} className="flex gap-2"><span className="text-secondary">•</span>{item}</li>)}
              </ul>
              {section.rewrite_examples.map((item) => (
                <div key={item} className="mt-2 rounded-xl bg-secondary/5 px-3 py-2 text-[10px] font-semibold leading-relaxed text-on-surface">{item}</div>
              ))}
            </div>
          ))}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-outline-variant/70 p-4">
          <ReportHeading title="岗位关键词匹配" />
          <KeywordGroup label="已匹配" values={report.job_match.matched_keywords} tone="matched" />
          <KeywordGroup label="待补足" values={report.job_match.gap_keywords} tone="gap" />
          <p className="mt-3 text-[10px] font-semibold leading-relaxed text-on-surface-variant">{report.job_match.guidance}</p>
        </div>
        <div className="rounded-2xl border border-outline-variant/70 p-4">
          <ReportHeading title="课程能力映射" count={report.course_capability_matches.length} />
          <div className="mt-3 space-y-2">
            {report.course_capability_matches.length === 0 ? (
              <p className="text-[10px] font-semibold text-outline">本次没有使用课程学习记录。</p>
            ) : report.course_capability_matches.map((item) => (
              <div key={`${item.course_name}-${item.capability}`} className="rounded-xl bg-surface-container-low p-3">
                <p className="text-[11px] font-black text-on-surface">{item.course_name} · {item.capability}</p>
                <p className="mt-1 text-[9px] leading-relaxed text-on-surface-variant">{item.progress_evidence}</p>
                <p className="mt-1 text-[10px] font-semibold leading-relaxed text-secondary">{item.suggested_wording}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="student-resume-draft rounded-3xl border border-secondary/20 p-4 sm:p-5">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-[10px] font-black uppercase tracking-[0.14em] text-secondary">Optimized Draft</p>
            <h3 className="mt-0.5 text-base font-black text-on-surface">优化后简历草稿</h3>
          </div>
          <button type="button" onClick={() => void onCopy('all', draftMarkdown)} className="inline-flex items-center gap-1.5 rounded-xl bg-secondary px-3 py-2 text-[10px] font-black text-white">
            {copiedKey === 'all' ? <Check className="h-3.5 w-3.5" /> : <ClipboardCopy className="h-3.5 w-3.5" />}
            {copiedKey === 'all' ? '已复制' : '复制完整草稿'}
          </button>
        </div>
        <div className="mt-4 space-y-3">
          {report.optimized_resume_sections.map((section, index) => {
            const key = `section-${index}`
            return (
              <article key={`${section.heading}-${index}`} className="rounded-2xl border border-outline-variant/60 bg-surface-container-lowest p-4">
                <div className="flex items-center justify-between gap-3">
                  <h4 className="text-xs font-black text-on-surface">{section.heading}</h4>
                  <button type="button" onClick={() => void onCopy(key, `## ${section.heading}\n\n${section.markdown}`)} className="inline-flex items-center gap-1 text-[9px] font-black text-secondary">
                    {copiedKey === key ? <Check className="h-3 w-3" /> : <ClipboardCopy className="h-3 w-3" />}
                    {copiedKey === key ? '已复制' : '复制本模块'}
                  </button>
                </div>
                <div className="mt-3 text-xs leading-relaxed text-on-surface-variant [&_h1]:font-black [&_h2]:font-black [&_li]:ml-4 [&_li]:list-disc [&_p]:my-1">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{section.markdown}</ReactMarkdown>
                </div>
              </article>
            )
          })}
        </div>
      </div>

      <p className="rounded-xl border border-dashed border-outline-variant px-3 py-2 text-[10px] font-semibold leading-relaxed text-outline">{report.evidence_notice}</p>
    </motion.section>
  )
}

function ReportHeading({ title, count }: { title: string; count?: number }) {
  return <h3 className="text-sm font-black text-on-surface">{title}{typeof count === 'number' && <span className="ml-2 text-[10px] text-outline">{count}</span>}</h3>
}

function KeywordGroup({ label, values, tone }: { label: string; values: string[]; tone: 'matched' | 'gap' }) {
  return (
    <div className="mt-3">
      <p className="text-[9px] font-black uppercase tracking-wider text-outline">{label}</p>
      <div className="mt-1.5 flex flex-wrap gap-1.5">
        {values.length === 0 ? <span className="text-[10px] font-semibold text-outline">暂无</span> : values.map((value) => (
          <span key={value} className={`rounded-full px-2 py-1 text-[9px] font-black ${tone === 'matched' ? 'bg-secondary/10 text-secondary' : 'bg-tertiary/10 text-tertiary'}`}>{value}</span>
        ))}
      </div>
    </div>
  )
}

function severityLabel(value: ResumeIssueSeverity): string {
  return value === 'high' ? '高优先级' : value === 'medium' ? '中优先级' : '低优先级'
}

function severityClass(value: ResumeIssueSeverity): string {
  return value === 'high'
    ? 'bg-error/10 text-error'
    : value === 'medium'
      ? 'bg-tertiary/10 text-tertiary'
      : 'bg-secondary/10 text-secondary'
}
