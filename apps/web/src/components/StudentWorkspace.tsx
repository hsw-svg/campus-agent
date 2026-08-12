import { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import {
  GraduationCap,
  BookOpen,
  BookOpenCheck,
  History,
  FolderOpen,
  ShieldCheck,
  Search,
  Activity,
  Bell,
  UserRoundCheck,
  Send,
  Paperclip,
  Mic,
  Image as ImageIcon,
  Compass,
  Sparkles,
  CheckCircle,
  Copy,
  Newspaper,
  LibraryBig,
  CircleCheckBig,
  FileUser,
  FileText,
  HelpCircle,
  ClipboardList,
  MessageSquare,
  Trash2,
  X,
} from 'lucide-react';
import { motion } from 'motion/react';
import {
  completeCourseChapter,
  downloadBlob,
  exportArtifact,
  getCourseDetail,
  initializeDefaultCourses,
  startCourse,
  startCourseChapter,
  type Artifact,
  type CourseDetail,
  type CourseSummary,
} from '../api';
import { Message } from '../types';
import { useWorkspaceChat } from '../hooks/useWorkspaceChat';
import ResourcePicker from './ResourcePicker';
import CampusNewsPanel from './CampusNewsPanel';
import CourseCenterPanel from './CourseCenterPanel';
import CourseDetailPanel from './CourseDetailPanel';
import ResumeAssistantPanel from './ResumeAssistantPanel';
import DeepTutorBookPanel from './DeepTutorBookPanel';
import DeepTutorLearningSpacePanel from './DeepTutorLearningSpacePanel';
import StudentOrbitHome from './StudentOrbitHome';

interface StudentWorkspaceProps {
  token: string | null;
  onBackToRoles: () => void;
}

type StudentSection = 'learning' | 'courses' | 'course-detail' | 'campus' | 'resume' | 'learning-space' | 'deep-tutor';

export default function StudentWorkspace({ token, onBackToRoles }: StudentWorkspaceProps) {
  const [activeSection, setActiveSection] = useState<StudentSection>('learning');
  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [courseDetail, setCourseDetail] = useState<CourseDetail | null>(null);
  const [learningCourse, setLearningCourse] = useState<CourseDetail | null>(null);
  const [learningChapterId, setLearningChapterId] = useState<string | null>(null);
  const [courseLoading, setCourseLoading] = useState(false);
  const [courseError, setCourseError] = useState<string | null>(null);
  const [deepTutorBookId, setDeepTutorBookId] = useState('');
  const [deepTutorPageId, setDeepTutorPageId] = useState('');
  const courseLoadAttemptedRef = useRef(false);
  const learningChapter = learningCourse?.chapters.find((chapter) => chapter.id === learningChapterId) ?? null;
  const courseContext = useMemo(() => learningCourse ? {
    courseId: learningCourse.id,
    courseName: learningCourse.name,
    chapterId: learningChapter?.id ?? null,
    chapterName: learningChapter?.title ?? '课程学习',
    workflowId: 'student-course-learning',
    workflowName: '课程学习',
  } : undefined, [learningChapter?.id, learningChapter?.title, learningCourse]);

  const {
    chatMessages,
    isAiTyping,
    sendMessage,
    clearChat,
    uploadFile,
    error,
    conversations,
    activeConversationId,
    openConversation,
    removeConversation,
    attachments,
    artifacts,
    citations,
    selectedAttachmentIds,
    selectedArtifactIds,
    toggleAttachment,
    toggleArtifact,
    stopStreaming,
    retryLastMessage,
    runStatus,
    toolStatus,
    route,
  } = useWorkspaceChat(token, courseContext);
  const [inputVal, setInputVal] = useState('');
  const [copied, setCopied] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [inputVal]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, isAiTyping]);

  useEffect(() => {
    if (!historyOpen) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setHistoryOpen(false);
    };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [historyOpen]);

  const handleSendMessage = (textToSend?: string) => {
    const finalMsg = textToSend || inputVal;
    if (!finalMsg.trim()) return;
    setInputVal('');
    void sendMessage(finalMsg);
  };

  const refreshCourses = useCallback(async () => {
    if (!token) return
    courseLoadAttemptedRef.current = true
    setCourseLoading(true)
    setCourseError(null)
    try {
      setCourses(await initializeDefaultCourses(token))
    } catch (reason) {
      setCourseError(reason instanceof Error ? reason.message : '课程加载失败，请稍后重试。')
    } finally {
      setCourseLoading(false)
    }
  }, [token])

  useEffect(() => {
    if ((activeSection === 'learning' || activeSection === 'courses') && courses.length === 0 && !courseLoadAttemptedRef.current) {
      void refreshCourses()
    }
  }, [activeSection, courses.length, refreshCourses])

  const showCourseCenter = () => {
    setActiveSection('courses')
    setCourseDetail(null)
  }

  const openCourseDetail = async (course: CourseSummary) => {
    if (!token) return
    setCourseLoading(true)
    setCourseError(null)
    try {
      const detail = await getCourseDetail(token, course.id)
      setCourseDetail(detail)
      setActiveSection('course-detail')
    } catch (reason) {
      setCourseError(reason instanceof Error ? reason.message : '课程详情加载失败。')
    } finally {
      setCourseLoading(false)
    }
  }

  const enterCourseLearning = async (course: CourseSummary | CourseDetail, chapterId?: string) => {
    if (!token) return
    setCourseLoading(true)
    setCourseError(null)
    try {
      const detail = chapterId
        ? await startCourseChapter(token, course.id, chapterId)
        : await startCourse(token, course.id)
      const nextChapterId = chapterId ?? detail.current_chapter_id ?? detail.chapters[0]?.id ?? null
      clearChat()
      setLearningCourse(detail)
      setLearningChapterId(nextChapterId)
      setCourseDetail(detail)
      setCourses((current) => current.map((item) => item.id === detail.id ? detail : item))
      setActiveSection('learning')
    } catch (reason) {
      setCourseError(reason instanceof Error ? reason.message : '无法开始课程学习。')
    } finally {
      setCourseLoading(false)
    }
  }

  const finishCurrentChapter = async () => {
    if (!token || !learningCourse || !learningChapterId || isAiTyping) return
    setCourseLoading(true)
    setCourseError(null)
    try {
      const detail = await completeCourseChapter(token, learningCourse.id, learningChapterId)
      clearChat()
      setLearningCourse(detail)
      setLearningChapterId(detail.current_chapter_id)
      setCourseDetail(detail)
      setCourses((current) => current.map((item) => item.id === detail.id ? detail : item))
    } catch (reason) {
      setCourseError(reason instanceof Error ? reason.message : '章节进度保存失败。')
    } finally {
      setCourseLoading(false)
    }
  }

  const copyText = (txt: string) => {
    navigator.clipboard.writeText(txt);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleExportArtifact = async (artifact: Artifact, format: 'markdown' | 'csv') => {
    if (!token) return;
    try {
      const blob = await exportArtifact(token, artifact.id, format);
      downloadBlob(blob, `${artifact.title || artifact.id}.${format === 'csv' ? 'csv' : 'md'}`);
      setExportError(null);
    } catch (reason) {
      setExportError(reason instanceof Error ? reason.message : '成果导出失败，请稍后重试。');
    }
  };

  const resourcePicker = (
    <ResourcePicker
      attachments={attachments}
      artifacts={artifacts}
      citations={citations}
      selectedAttachmentIds={selectedAttachmentIds}
      selectedArtifactIds={selectedArtifactIds}
      accentClass="text-secondary"
      onToggleAttachment={toggleAttachment}
      onToggleArtifact={toggleArtifact}
      onExport={handleExportArtifact}
    />
  );

  return (
    <div className="student-orbit-shell flex h-screen w-full overflow-hidden bg-background font-sans text-on-surface antialiased">
      
      {/* MAIN CONTENT AREA */}
      <main className="relative flex h-screen min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-background">
        {activeSection === 'learning' && (error || exportError) && <div role="alert" className="mx-10 mt-3 rounded-xl border border-error/30 bg-error-container px-4 py-2 text-xs text-on-error-container">{error || exportError}</div>}
        {activeSection === 'learning' && courseError && <div role="alert" className="mx-10 mt-3 rounded-xl border border-error/30 bg-error-container px-4 py-2 text-xs text-on-error-container">{courseError}</div>}
        {activeSection === 'learning' && (toolStatus || route || runStatus === 'failed' || runStatus === 'needs_input') && (
          <div className="mx-10 mt-3 flex flex-wrap items-center gap-2 rounded-xl border border-secondary/20 bg-secondary-container/10 px-4 py-2 text-xs text-on-surface-variant">
            {toolStatus && <span className="font-semibold text-secondary">{toolStatus}</span>}
            {route?.agentName && <span>当前智能体：{route.agentName}</span>}
            {(runStatus === 'failed' || runStatus === 'needs_input') && !isAiTyping && (
              <button type="button" onClick={retryLastMessage} className="rounded-lg border border-secondary/30 px-2.5 py-1 font-bold text-secondary hover:bg-secondary-container/25">重试上一次任务</button>
            )}
          </div>
        )}
        
        {/* Top App Bar */}
        <header className="sticky top-0 z-40 flex h-14 shrink-0 items-center justify-between border-b border-outline-variant/70 bg-surface-container-low/90 px-4 shadow-[0_8px_30px_rgba(0,5,20,0.2)] backdrop-blur-xl sm:px-6 lg:px-8">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex shrink-0 items-center gap-2 text-secondary" aria-label="智汇校园学生端">
              <BookOpen className="h-5 w-5" />
              <span className="hidden text-sm font-black sm:inline">智汇校园</span>
            </div>
            <span className="hidden h-5 w-px bg-outline-variant sm:block" aria-hidden="true" />
            <div className="flex items-center gap-2 rounded-lg border border-outline-variant/80 bg-surface-container px-3 py-1.5">
              <ShieldCheck className="w-4 h-4 text-secondary" />
              <span className="text-xs font-bold text-on-surface-variant">匿名学习空间</span>
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-2">
            <button
              type="button"
              onClick={() => setHistoryOpen(true)}
              className="flex min-h-10 items-center gap-1.5 rounded-lg border border-outline-variant bg-surface-container px-3 py-2 text-xs font-semibold text-on-surface-variant transition-colors hover:border-secondary/50 hover:text-secondary"
            >
              <History className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">最近对话</span>
              {conversations.length > 0 && <span className="tabular-nums text-secondary">{conversations.length}</span>}
            </button>
            <button
              type="button"
              onClick={onBackToRoles}
              className="flex min-h-10 items-center gap-1.5 rounded-lg border border-outline-variant bg-surface-container px-3 py-2 text-xs font-semibold text-on-surface-variant transition-colors hover:border-secondary/50 hover:text-secondary"
            >
              <UserRoundCheck className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">切换角色</span>
            </button>
          </div>
        </header>

        <nav className="student-agent-trail" aria-label="学生智能体导航">
          <button type="button" aria-current={activeSection === 'learning' ? 'page' : undefined} data-active={activeSection === 'learning'} onClick={() => { clearChat(); setLearningCourse(null); setLearningChapterId(null); setActiveSection('learning') }}>
            <Compass /><span><small>学习智能体</small>学习中心</span>
          </button>
          <button type="button" aria-current={activeSection === 'courses' || activeSection === 'course-detail' ? 'page' : undefined} data-active={activeSection === 'courses' || activeSection === 'course-detail'} onClick={showCourseCenter}>
            <LibraryBig /><span><small>课程智能体</small>课程中心</span>
          </button>
          <button type="button" aria-current={activeSection === 'learning-space' ? 'page' : undefined} data-active={activeSection === 'learning-space'} onClick={() => setActiveSection('learning-space')}>
            <Sparkles /><span><small>知识智能体</small>学习空间</span>
          </button>
          <button type="button" aria-current={activeSection === 'deep-tutor' ? 'page' : undefined} data-active={activeSection === 'deep-tutor'} onClick={() => { setDeepTutorBookId(''); setDeepTutorPageId(''); setActiveSection('deep-tutor') }}>
            <BookOpenCheck /><span><small>教材智能体</small>交互教材</span>
          </button>
          <button type="button" aria-current={activeSection === 'campus' ? 'page' : undefined} data-active={activeSection === 'campus'} onClick={() => setActiveSection('campus')}>
            <Newspaper /><span><small>校园智能体</small>校园中心</span>
          </button>
          <button type="button" aria-current={activeSection === 'resume' ? 'page' : undefined} data-active={activeSection === 'resume'} onClick={() => setActiveSection('resume')}>
            <FileUser /><span><small>成长智能体</small>简历助手</span>
          </button>
        </nav>

        {/* Chat / Workbench layout */}
        <div className="flex min-h-0 min-w-0 flex-1 overflow-hidden">
          
          <div className="flex h-full min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
            <section className={`mx-auto flex min-h-0 min-w-0 w-full flex-1 flex-col overflow-y-auto ${
              activeSection === 'resume'
                ? 'max-w-none p-3 sm:p-4 xl:overflow-hidden xl:p-0'
                : activeSection === 'learning' && chatMessages.length === 0
                  ? 'max-w-none overflow-hidden p-0'
                  : `space-y-6 p-4 sm:p-6 ${activeSection === 'campus' || activeSection === 'courses' || activeSection === 'course-detail' || activeSection === 'learning-space' || activeSection === 'deep-tutor' ? 'max-w-7xl' : 'max-w-4xl'}`
            }`}>

            {activeSection === 'resume' && <ResumeAssistantPanel token={token} />}

            {activeSection === 'campus' && (
              <div className="w-full py-4 sm:py-8">
                <CampusNewsPanel />
              </div>
            )}

            {activeSection === 'learning-space' && (
              <DeepTutorLearningSpacePanel
                token={token}
                onOpenBooks={(bookId, pageId) => {
                  setDeepTutorBookId(bookId ?? '')
                  setDeepTutorPageId(pageId ?? '')
                  setActiveSection('deep-tutor')
                }}
              />
            )}

            {activeSection === 'deep-tutor' && <DeepTutorBookPanel token={token} initialBookId={deepTutorBookId} initialPageId={deepTutorPageId} />}

            {activeSection === 'courses' && (
              <CourseCenterPanel
                courses={courses}
                loading={courseLoading}
                error={courseError}
                onRetry={() => { void refreshCourses() }}
                onOpen={(course) => { void openCourseDetail(course) }}
                onStart={(course) => { void enterCourseLearning(course) }}
              />
            )}

            {activeSection === 'course-detail' && courseDetail && (
              <CourseDetailPanel
                course={courseDetail}
                loading={courseLoading}
                onBack={showCourseCenter}
                onStart={(chapterId) => { void enterCourseLearning(courseDetail, chapterId) }}
              />
            )}

            {activeSection === 'learning' && learningCourse && learningChapter && (
              <div className="flex flex-col gap-3 rounded-2xl border border-secondary/25 bg-secondary-container/10 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <p className="text-[10px] font-black uppercase tracking-[0.18em] text-secondary">当前课程 · {learningCourse.progress_percent}%</p>
                  <p className="mt-1 truncate text-sm font-black text-on-surface">{learningCourse.name} · {learningChapter.title}</p>
                </div>
                <div className="flex shrink-0 gap-2">
                  <button type="button" onClick={() => { setCourseDetail(learningCourse); setActiveSection('course-detail') }} className="rounded-xl border border-secondary/25 px-3 py-2 text-[11px] font-black text-secondary hover:bg-secondary-container/20">
                    查看课程详情
                  </button>
                  <button type="button" disabled={courseLoading || isAiTyping} onClick={() => { void finishCurrentChapter() }} className="inline-flex items-center gap-1.5 rounded-xl bg-secondary px-3 py-2 text-[11px] font-black text-on-secondary disabled:opacity-50">
                    <CircleCheckBig className="h-4 w-4" />完成本节学习
                  </button>
                </div>
              </div>
            )}

            {activeSection === 'learning' && chatMessages.length === 0 && (
              <StudentOrbitHome
                courses={courses}
                learningCourse={learningCourse}
                learningChapterId={learningChapterId}
                loading={courseLoading}
                onOpenCourses={showCourseCenter}
                onStartCourse={(course, chapterId) => { void enterCourseLearning(course, chapterId) }}
                onOpenBook={() => { setDeepTutorBookId(''); setDeepTutorPageId(''); setActiveSection('deep-tutor') }}
                onOpenLearningSpace={() => setActiveSection('learning-space')}
                onAsk={(prompt) => handleSendMessage(prompt)}
              />
            )}

            {activeSection === 'learning' && chatMessages.length > 0 && (
              <div className="space-y-6">
                {chatMessages.map((msg, idx) => {
                  const isUser = msg.sender === 'user';
                  return (
                    <div key={msg.id} className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
                      {!isUser && (
                        <div className="w-8 h-8 rounded-full bg-secondary-container flex items-center justify-center text-on-secondary-container shrink-0 border border-outline-variant">
                          <BookOpen className="w-4 h-4" />
                        </div>
                      )}
                      
                      <div className={`max-w-[85%] rounded-2xl px-5 py-4 shadow-xs ${
                        isUser 
                          ? 'bg-secondary text-on-secondary rounded-tr-none' 
                          : 'bg-surface-container-lowest border border-outline-variant/60 text-on-surface rounded-tl-none'
                      }`}>
                        <div className="text-xs opacity-70 mb-1 flex items-center justify-between">
                          <span>{isUser ? '学生（您）' : '学生智能助手'}</span>
                          <span>{msg.timestamp}</span>
                        </div>
                        <div className="text-sm leading-relaxed whitespace-pre-line prose prose-sm max-w-none">
                          {msg.content}
                        </div>
                        
                        {!isUser && (
                          <button 
                            onClick={() => copyText(msg.content)}
                            className="mt-3 flex items-center gap-1 px-3 py-1.5 bg-surface-container hover:bg-surface-container-high rounded-lg text-xs font-semibold cursor-pointer border border-outline-variant"
                          >
                            <Copy className="w-3.5 h-3.5" />
                            {copied ? '复制成功！' : '复制资料方案'}
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}

                {isAiTyping && (
                  <div className="flex gap-3 justify-start items-center">
                    <div className="w-8 h-8 rounded-full bg-secondary-container flex items-center justify-center text-on-secondary-container shrink-0">
                      <BookOpen className="w-4 h-4" />
                    </div>
                    <div className="bg-surface-container-lowest border border-outline-variant/60 rounded-2xl px-5 py-4 text-xs font-semibold text-on-surface-variant flex items-center gap-2">
                      <span className="animate-pulse">学生智能助手正在提炼课程纲领与要点</span>
                      <span className="flex gap-0.5">
                        <span className="h-1 w-1 animate-pulse rounded-full bg-secondary"></span>
                        <span className="h-1 w-1 animate-pulse rounded-full bg-secondary [animation-delay:0.2s]"></span>
                        <span className="h-1 w-1 animate-pulse rounded-full bg-secondary [animation-delay:0.4s]"></span>
                      </span>
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>
            )}
          </section>

          {/* Input Footer */}
          {activeSection === 'learning' && chatMessages.length > 0 && <div className="px-6 pb-3 xl:hidden">{resourcePicker}</div>}
          {activeSection === 'learning' && chatMessages.length > 0 && <div className="z-10 mt-auto shrink-0 border-t border-outline-variant/30 bg-background px-4 pb-5 pt-2 sm:px-6 lg:px-10 lg:pb-6">
            <div className="max-w-4xl mx-auto space-y-3">
              <div className="flex gap-2 overflow-x-auto scrollbar-hide py-1">
                <button 
                  onClick={() => handleSendMessage('论文辅助：生成计算机大模型相关大纲')}
                  className="inline-flex min-h-11 items-center gap-1.5 whitespace-nowrap rounded-full border border-outline-variant bg-surface-container px-3 py-2 text-[11px] font-bold text-on-surface-variant transition-colors hover:bg-surface-container-high"
                >
                  <FileText className="h-3.5 w-3.5" />论文大纲构思
                </button>
                <button 
                  onClick={() => handleSendMessage('知识问答：Python 列表与元组的深度区别')}
                  className="inline-flex min-h-11 items-center gap-1.5 whitespace-nowrap rounded-full border border-outline-variant bg-surface-container px-3 py-2 text-[11px] font-bold text-on-surface-variant transition-colors hover:bg-surface-container-high"
                >
                  <HelpCircle className="h-3.5 w-3.5" />算法概念答疑
                </button>
                <button 
                  onClick={() => handleSendMessage('课程总结：自动生成 Python 复习备考冲刺计划')}
                  className="inline-flex min-h-11 items-center gap-1.5 whitespace-nowrap rounded-full border border-outline-variant bg-surface-container px-3 py-2 text-[11px] font-bold text-on-surface-variant transition-colors hover:bg-surface-container-high"
                >
                  <ClipboardList className="h-3.5 w-3.5" />期末复习冲刺
                </button>
              </div>

              <div className="bg-surface-container-lowest rounded-2xl shadow-xs border-2 border-outline-variant focus-within:border-secondary transition-all p-3">
                <textarea 
                  ref={textareaRef}
                  value={inputVal}
                  onChange={(e) => setInputVal(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSendMessage();
                    }
                  }}
                  className="w-full bg-transparent border-none outline-none focus:outline-hidden text-sm p-1 resize-none font-sans leading-relaxed text-on-surface min-h-[44px] scrollbar-hide" 
                  placeholder="提问你的学术盲点或概念..." 
                  aria-label="向学生智能助手提问"
                  rows={2}
                />
                <div className="flex items-center justify-between pt-2 border-t border-outline-variant/35">
                  <div className="flex gap-1">
                    <button type="button" aria-label="上传学习资料" onClick={() => fileInputRef.current?.click()} className="grid h-11 w-11 place-items-center rounded-lg text-outline transition-colors hover:bg-surface-container hover:text-secondary">
                      <Paperclip className="w-4 h-4" />
                    </button>
                    <input ref={fileInputRef} type="file" className="hidden" accept=".txt,.md,.docx,.pdf,.xlsx,.csv" onChange={(event) => { const file = event.target.files?.[0]; if (file) void uploadFile(file); event.currentTarget.value = ''; }} />
                    <button type="button" aria-label="使用语音输入" className="grid h-11 w-11 place-items-center rounded-lg text-outline transition-colors hover:bg-surface-container hover:text-secondary">
                      <Mic className="w-4 h-4" />
                    </button>
                  </div>
                  
                  <button 
                    onClick={() => isAiTyping ? stopStreaming() : handleSendMessage()}
                    className="bg-secondary text-on-secondary px-5 py-2 rounded-xl font-bold text-xs flex items-center gap-1.5 active:scale-95 transition-all cursor-pointer hover:bg-opacity-95 shadow-sm"
                  >
                    <span>{isAiTyping ? '停止生成' : '发送指令'}</span>
                    {isAiTyping ? <span className="h-3 w-3 rounded-sm bg-on-secondary" /> : <Send className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>
            </div>
          </div>}
          </div>

          {/* Right sidebar */}
          {activeSection === 'learning' && chatMessages.length > 0 && <aside className="hidden h-full w-80 shrink-0 flex-col gap-6 overflow-y-auto border-l border-outline-variant bg-surface-container-low p-4 xl:flex">
            {resourcePicker}
            <div className="space-y-3">
              <h3 className="text-[11px] font-bold text-on-surface-variant uppercase tracking-wider px-1">学习备考资料袋</h3>
              <div className="bg-surface-container-lowest border border-outline-variant/60 p-4 rounded-xl space-y-2">
                <p className="text-xs font-bold text-on-surface">我的期末复习档案</p>
                <div className="flex items-center gap-2 text-xs text-on-surface-variant">
                  <CheckCircle className="w-4 h-4 text-secondary" />
                  <span>Python 切片练习：已刷 3 次</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-on-surface-variant">
                  <CheckCircle className="w-4 h-4 text-secondary" />
                  <span>大一元组内存测试：完美掌握</span>
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <h3 className="text-[11px] font-bold text-on-surface-variant tracking-wider px-1">智能学习辅导进度</h3>
              <div className="bg-surface-container-lowest border border-outline-variant/60 p-4 rounded-xl space-y-2">
                <div className="h-1.5 w-full bg-surface-container-high rounded-full overflow-hidden">
                  <div className="h-full bg-secondary w-2/3"></div>
                </div>
                <p className="text-[10px] text-outline">今天已学习 2/3 的难点。继续加油！</p>
              </div>
            </div>
          </aside>}

        </div>
      </main>

      {historyOpen && (
        <div className="student-history-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setHistoryOpen(false) }}>
          <section role="dialog" aria-modal="true" aria-labelledby="student-history-title" className="student-history-dialog">
            <header>
              <div>
                <History aria-hidden="true" />
                <div>
                  <h2 id="student-history-title">最近对话</h2>
                  <p>继续之前的学习任务，或清理不再需要的记录。</p>
                </div>
              </div>
              <button type="button" onClick={() => setHistoryOpen(false)} aria-label="关闭最近对话">
                <X />
              </button>
            </header>
            <div className="student-history-list">
              {conversations.filter((conversation) => conversation.agent_id !== 'resume_helper' && (learningCourse
                ? conversation.course_id === learningCourse.id && conversation.chapter_id === learningChapterId
                : conversation.course_id === null)).length === 0 ? (
                <div className="student-history-empty">
                  <MessageSquare aria-hidden="true" />
                  <strong>暂无历史对话</strong>
                  <span>开始学习或向 AI 学伴提问后，对话会保存在这里。</span>
                </div>
              ) : conversations.filter((conversation) => conversation.agent_id !== 'resume_helper' && (learningCourse
                ? conversation.course_id === learningCourse.id && conversation.chapter_id === learningChapterId
                : conversation.course_id === null)).map((conversation) => (
                  <div key={conversation.id} className="student-history-item" data-active={activeConversationId === conversation.id}>
                    <button type="button" onClick={() => { setActiveSection('learning'); setHistoryOpen(false); void openConversation(conversation.id) }}>
                      <MessageSquare aria-hidden="true" />
                      <span>
                        <strong>{conversation.title || '未命名对话'}</strong>
                        <small>{activeConversationId === conversation.id ? '当前对话' : '点击继续学习'}</small>
                      </span>
                    </button>
                    <button type="button" onClick={() => { void removeConversation(conversation.id) }} aria-label={`删除对话：${conversation.title || '未命名对话'}`}>
                      <Trash2 />
                    </button>
                  </div>
                ))}
            </div>
          </section>
        </div>
      )}

    </div>
  );
}
