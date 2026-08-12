import { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import {
  BookOpen,
  BookOpenCheck,
  History,
  ShieldCheck,
  UserRoundCheck,
  Send,
  Paperclip,
  Mic,
  Compass,
  Sparkles,
  Copy,
  Newspaper,
  LibraryBig,
  CircleCheckBig,
  FileUser,
  MessageSquare,
  Trash2,
  X,
} from 'lucide-react';
import {
  completeCourseChapter,
  getCourseDetail,
  initializeDefaultCourses,
  startCourse,
  startCourseChapter,
  type CourseDetail,
  type CourseSummary,
} from '../api';
import { useWorkspaceChat } from '../hooks/useWorkspaceChat';
import CampusNewsPanel from './CampusNewsPanel';
import CourseCenterPanel from './CourseCenterPanel';
import CourseDetailPanel from './CourseDetailPanel';
import ResumeAssistantPanel from './ResumeAssistantPanel';
import DeepTutorBookPanel from './DeepTutorBookPanel';
import DeepTutorLearningSpacePanel from './DeepTutorLearningSpacePanel';
import StudentOrbitHome, { type TutorRoleId } from './StudentOrbitHome';

interface StudentWorkspaceProps {
  token: string | null;
  onBackToRoles: () => void;
}

type StudentSection = 'learning' | 'courses' | 'course-detail' | 'campus' | 'resume' | 'learning-space' | 'deep-tutor';

function visibleStudentPrompt(content: string): string {
  const marker = '\n\n用户问题：'
  const markerIndex = content.indexOf(marker)
  return markerIndex >= 0 ? content.slice(markerIndex + marker.length) : content
}

const tutorRoleInstructions: Record<TutorRoleId, string> = {
  default: '请使用 DeepTutor 默认角色。以均衡学伴方式回答：先给清晰结论，再用简短例子和下一步学习建议帮助理解。',
  peer: '请使用 DeepTutor 的 peer 角色。像同学共同讨论：语气平等亲和，多用生活化类比和启发式追问，鼓励学生先表达自己的理解，不使用居高临下的讲授口吻。',
  'research-assistant': '请使用 DeepTutor 的 research-assistant 角色。像研究助理分析：明确概念边界、关键假设、证据与推理链，区分事实和推断，并给出可以继续验证或检索的问题。',
  teacher: '请使用 DeepTutor 的 teacher 角色。像导师结构化教学：先说明学习目标，再分层讲解核心知识点，穿插典型例子，最后用检查问题确认学生是否掌握。',
}

export default function StudentWorkspace({ token, onBackToRoles }: StudentWorkspaceProps) {
  const [activeSection, setActiveSection] = useState<StudentSection>('learning');
  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [courseDetail, setCourseDetail] = useState<CourseDetail | null>(null);
  const [learningCourse, setLearningCourse] = useState<CourseDetail | null>(null);
  const [learningChapterId, setLearningChapterId] = useState<string | null>(null);
  const [learningSessionOpen, setLearningSessionOpen] = useState(false);
  const [selectedTutorRole, setSelectedTutorRole] = useState<TutorRoleId>('default');
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
    stopStreaming,
    retryLastMessage,
    runStatus,
    toolStatus,
    route,
  } = useWorkspaceChat(token, courseContext);
  const [inputVal, setInputVal] = useState('');
  const [copied, setCopied] = useState(false);
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
    const roleInstruction = tutorRoleInstructions[selectedTutorRole];
    setInputVal('');
    setLearningSessionOpen(true);
    void sendMessage(`${roleInstruction}\n\n用户问题：${finalMsg.trim()}`);
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
      setLearningSessionOpen(true)
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

  const sharedComposer = (
    <div className="student-shared-composer">
      <textarea
        ref={textareaRef}
        value={inputVal}
        onChange={(event) => setInputVal(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            handleSendMessage();
          }
        }}
        className="student-shared-composer-input"
        placeholder="提问课程知识、学习方法或练习…"
        aria-label="向学生智能助手提问"
        rows={2}
      />
      <div className="student-shared-composer-tools">
        <div>
          <button type="button" aria-label="上传学习资料" onClick={() => fileInputRef.current?.click()}>
            <Paperclip />
          </button>
          <input ref={fileInputRef} type="file" className="hidden" accept=".txt,.md,.docx,.pdf,.xlsx,.csv" onChange={(event) => { const file = event.target.files?.[0]; if (file) void uploadFile(file); event.currentTarget.value = ''; }} />
          <button type="button" aria-label="使用语音输入"><Mic /></button>
          {attachments.length > 0 && <span className="student-shared-composer-attachment">已添加 {attachments.length} 份资料</span>}
        </div>
        <button type="button" onClick={() => isAiTyping ? stopStreaming() : handleSendMessage()} disabled={!isAiTyping && !inputVal.trim()}>
          <span>{isAiTyping ? '停止生成' : '发送指令'}</span>
          {isAiTyping ? <span className="student-shared-composer-stop" /> : <Send />}
        </button>
      </div>
    </div>
  );

  const orbitConversationContent = (
    <div className="student-orbit-conversation-scroll">
      {learningCourse && learningChapter && (
        <header className="student-orbit-conversation-heading">
          <div><small>当前课程 · {learningCourse.progress_percent}%</small><strong>{learningCourse.name} · {learningChapter.title}</strong></div>
          <button type="button" disabled={courseLoading || isAiTyping} onClick={() => { void finishCurrentChapter() }}>
            <CircleCheckBig />完成本节学习
          </button>
        </header>
      )}
      {chatMessages.length === 0 && learningCourse && learningChapter && (
        <div className="student-learning-arrival">
          <span><Sparkles />学习航线已定位</span>
          <h2>{learningChapter.title}</h2>
          <p>课程已进入当前章节。可以直接提问，或让 AI 学伴规划本节学习。</p>
        </div>
      )}
      <div className="student-orbit-message-list">
        {chatMessages.map((msg) => {
          const isUser = msg.sender === 'user';
          return (
            <div key={msg.id} className={`student-orbit-message ${isUser ? 'is-user' : 'is-assistant'}`}>
              {!isUser && <span className="student-orbit-message-avatar"><BookOpen /></span>}
              <div>
                <header><span>{isUser ? '学生（您）' : '学生智能助手'}</span><time>{msg.timestamp}</time></header>
                <div className="student-orbit-message-content">{isUser ? visibleStudentPrompt(msg.content) : msg.content}</div>
                {!isUser && msg.content && (
                  <button type="button" onClick={() => copyText(msg.content)} className="student-orbit-message-copy">
                    <Copy />{copied ? '复制成功！' : '复制回答'}
                  </button>
                )}
              </div>
            </div>
          );
        })}
        {isAiTyping && (
          <div className="student-orbit-message is-assistant">
            <span className="student-orbit-message-avatar"><BookOpen /></span>
            <div className="student-orbit-thinking"><span>AI 学伴正在思考</span><i /><i /><i /></div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>
    </div>
  );

  return (
    <div className="student-orbit-shell flex h-screen w-full overflow-hidden bg-background font-sans text-on-surface antialiased">
      
      {/* MAIN CONTENT AREA */}
      <main className="relative flex h-screen min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-background">
        {activeSection === 'learning' && error && <div role="alert" className="mx-10 mt-3 rounded-xl border border-error/30 bg-error-container px-4 py-2 text-xs text-on-error-container">{error}</div>}
        {activeSection === 'learning' && courseError && <div role="alert" className="mx-10 mt-3 rounded-xl border border-error/30 bg-error-container px-4 py-2 text-xs text-on-error-container">{courseError}</div>}
        {activeSection === 'learning' && ((isAiTyping && (toolStatus || route)) || runStatus === 'failed' || runStatus === 'needs_input') && (
          <div className="mx-10 mt-3 flex flex-wrap items-center gap-2 rounded-xl border border-secondary/20 bg-secondary-container/10 px-4 py-2 text-xs text-on-surface-variant">
            {toolStatus && <span className="font-semibold text-secondary">{toolStatus}</span>}
            {route?.agentName && <span>当前智能体：{route.agentName}</span>}
            {(runStatus === 'failed' || runStatus === 'needs_input') && !isAiTyping && (
              <button type="button" onClick={retryLastMessage} className="rounded-lg border border-secondary/30 px-2.5 py-1 font-bold text-secondary hover:bg-secondary-container/25">重试上一次任务</button>
            )}
          </div>
        )}
        
        <nav className="student-agent-trail" aria-label="学生智能体导航">
          <div className="student-agent-trail-brand" aria-label="智汇校园匿名学习空间">
            <span><BookOpen /></span>
            <span><strong>智汇校园</strong><small><ShieldCheck />匿名学习空间</small></span>
          </div>

          <div className="student-agent-trail-links">
            <button type="button" aria-current={activeSection === 'learning' ? 'page' : undefined} data-active={activeSection === 'learning'} onClick={() => { clearChat(); setLearningCourse(null); setLearningChapterId(null); setLearningSessionOpen(false); setActiveSection('learning') }}>
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
          </div>

          <div className="student-agent-trail-actions">
            <button
              type="button"
              onClick={() => setHistoryOpen(true)}
              aria-label={`最近对话${conversations.length > 0 ? `，${conversations.length} 条` : ''}`}
            >
              <History className="h-3.5 w-3.5" />
              <span>最近对话</span>
              {conversations.length > 0 && <span className="tabular-nums text-secondary">{conversations.length}</span>}
            </button>
            <button
              type="button"
              onClick={onBackToRoles}
              aria-label="切换角色"
            >
              <UserRoundCheck className="w-3.5 h-3.5" />
              <span>切换角色</span>
            </button>
          </div>
        </nav>

        {/* Chat / Workbench layout */}
        <div className="flex min-h-0 min-w-0 flex-1 overflow-hidden">
          
          <div className="flex h-full min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
            <section className={`mx-auto flex min-h-0 min-w-0 w-full flex-1 flex-col overflow-y-auto ${
              activeSection === 'resume'
                ? 'max-w-none p-3 sm:p-4 xl:overflow-hidden xl:p-0'
                : activeSection === 'deep-tutor'
                  ? 'max-w-none overflow-hidden p-2 sm:p-3'
                : activeSection === 'learning'
                  ? 'max-w-none overflow-hidden p-0'
                  : `space-y-6 p-4 sm:p-6 ${activeSection === 'campus' || activeSection === 'courses' || activeSection === 'course-detail' || activeSection === 'learning-space' ? 'max-w-7xl' : 'max-w-4xl'}`
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

            {activeSection === 'learning' && (
              <StudentOrbitHome
                courses={courses}
                learningCourse={learningCourse}
                learningChapterId={learningChapterId}
                loading={courseLoading}
                onOpenCourses={showCourseCenter}
                onStartCourse={(course, chapterId) => enterCourseLearning(course, chapterId)}
                onOpenBook={() => { setDeepTutorBookId(''); setDeepTutorPageId(''); setActiveSection('deep-tutor') }}
                onOpenLearningSpace={() => setActiveSection('learning-space')}
                onAsk={(prompt) => handleSendMessage(prompt)}
                selectedRoleId={selectedTutorRole}
                onSelectRole={setSelectedTutorRole}
                composer={sharedComposer}
                conversationActive={learningSessionOpen || chatMessages.length > 0}
                conversationContent={orbitConversationContent}
              />
            )}
          </section>

          </div>

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
