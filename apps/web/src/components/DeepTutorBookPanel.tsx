import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import {
  ArrowLeft,
  BookOpenCheck,
  Bookmark,
  Check,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Database,
  FileText,
  Layers3,
  Lightbulb,
  LoaderCircle,
  MessageCircleQuestion,
  NotebookPen,
  Plus,
  Search,
  Send,
  Sparkles,
  Target,
} from 'lucide-react'
import {
  buildDeepTutorPageChatMessage,
  createDeepTutorBook,
  deepTutorBooksFromResponse,
  deepTutorKnowledgeBasesFromResponse,
  deepTutorPageFromResponse,
  deepTutorSpineFromResponse,
  getDeepTutorChatWebSocketUrl,
  getDeepTutorPage,
  getDeepTutorSpine,
  listDeepTutorBooks,
  listDeepTutorKnowledgeBases,
  parseDeepTutorChatEvent,
  type DeepTutorBlock,
  type DeepTutorBook,
  type DeepTutorChatEvent,
  type DeepTutorKnowledgeBase,
  type DeepTutorPage,
  type DeepTutorSpineItem,
} from '../api'
import useDeepTutorStudyState, { type DeepTutorChatMessage } from '../hooks/useDeepTutorStudyState'

interface DeepTutorBookPanelProps {
  token: string | null
  initialBookId?: string
  initialPageId?: string
}

type TutorMessage = DeepTutorChatMessage

function studentReadableBooks(value: unknown): DeepTutorBook[] {
  return deepTutorBooksFromResponse(value).filter((book) => book.status !== 'draft' || (book.pageCount ?? 0) > 0)
}

function blockTone(type: string): { label: string; tone: string; Icon: typeof Lightbulb } {
  if (['callout', 'tip', 'hint', 'highlight'].some((item) => type.includes(item))) {
    return { label: '学习提示', tone: 'tip', Icon: Lightbulb }
  }
  if (['quiz', 'question', 'exercise', 'practice'].some((item) => type.includes(item))) {
    return { label: '练习一下', tone: 'practice', Icon: Target }
  }
  return { label: '知识内容', tone: 'content', Icon: FileText }
}

function BookBlock({ block }: { block: DeepTutorBlock }) {
  const tone = blockTone(block.type)
  const Icon = tone.Icon
  return (
    <div className="deep-reader-block" data-tone={tone.tone}>
      <div className="deep-reader-block-heading">
        <Icon />
        <span>{block.title || tone.label}</span>
      </div>
      <div className="deep-reader-markdown prose prose-sm max-w-none">
        <ReactMarkdown>{block.content || '本内容块暂时没有可显示的文字。'}</ReactMarkdown>
      </div>
    </div>
  )
}

export default function DeepTutorBookPanel({ token, initialBookId, initialPageId }: DeepTutorBookPanelProps) {
  const [books, setBooks] = useState<DeepTutorBook[]>([])
  const [knowledgeBases, setKnowledgeBases] = useState<DeepTutorKnowledgeBase[]>([])
  const [selectedBookId, setSelectedBookId] = useState(initialBookId ?? '')
  const [spine, setSpine] = useState<DeepTutorSpineItem[]>([])
  const [selectedPageId, setSelectedPageId] = useState('')
  const [page, setPage] = useState<DeepTutorPage | null>(null)
  const [bookFilter, setBookFilter] = useState('')
  const [topic, setTopic] = useState('')
  const [selectedKnowledgeBase, setSelectedKnowledgeBase] = useState('')
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState<TutorMessage[]>([])
  const [messagesPageKey, setMessagesPageKey] = useState('')
  const [noteDraft, setNoteDraft] = useState('')
  const [noteSaved, setNoteSaved] = useState(false)
  const [loading, setLoading] = useState(true)
  const [pageLoading, setPageLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [chatting, setChatting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [chatError, setChatError] = useState<string | null>(null)
  const socketRef = useRef<WebSocket | null>(null)
  const sessionIdRef = useRef<string | null>(null)
  const requestIdRef = useRef(0)
  const studyState = useDeepTutorStudyState(token)
  const studyStateRef = useRef(studyState.state)
  const {
    state,
    completedForBook,
    isPageCompleted,
    markPageCompleted,
    setPageNote,
    saveQuestion,
    setChatHistory,
    clearChatHistory,
    setChatSession,
    setLastOpened,
  } = studyState

  useEffect(() => {
    studyStateRef.current = state
  }, [state])

  const selectedBook = useMemo(() => books.find((book) => book.id === selectedBookId) ?? null, [books, selectedBookId])
  const selectedSpineIndex = useMemo(() => spine.findIndex((item) => item.id === selectedPageId), [selectedPageId, spine])
  const selectedSpineItem = selectedSpineIndex >= 0 ? spine[selectedSpineIndex] : null
  const filteredBooks = useMemo(() => {
    const query = bookFilter.trim().toLowerCase()
    return query ? books.filter((book) => `${book.title} ${book.description}`.toLowerCase().includes(query)) : books
  }, [bookFilter, books])
  const currentCompletedPages = selectedBookId ? completedForBook(selectedBookId) : []
  const currentProgress = spine.length > 0 ? Math.round((currentCompletedPages.length / spine.length) * 100) : 0
  const pageNoteKey = selectedBookId && selectedPageId ? `${selectedBookId}:${selectedPageId}` : ''

  const closeSocket = useCallback(() => {
    socketRef.current?.close()
    socketRef.current = null
    setChatting(false)
  }, [])

  useEffect(() => () => closeSocket(), [closeSocket])

  useEffect(() => {
    if (!token) {
      setLoading(false)
      setError('当前学生工作空间尚未建立，暂时无法打开交互教材。')
      return
    }
    let active = true
    setLoading(true)
    setError(null)
    void Promise.allSettled([listDeepTutorBooks(token), listDeepTutorKnowledgeBases(token)]).then((results) => {
      if (!active) return
      const [booksResult, knowledgeResult] = results
      if (booksResult.status === 'fulfilled') {
        const nextBooks = studentReadableBooks(booksResult.value)
        setBooks(nextBooks)
        setSelectedBookId((current) => {
          if (initialBookId && nextBooks.some((book) => book.id === initialBookId)) return initialBookId
          return current && nextBooks.some((book) => book.id === current) ? current : nextBooks[0]?.id ?? ''
        })
      } else {
        setError(booksResult.reason instanceof Error ? booksResult.reason.message : '交互教材加载失败。')
      }
      if (knowledgeResult.status === 'fulfilled') setKnowledgeBases(deepTutorKnowledgeBasesFromResponse(knowledgeResult.value))
      setLoading(false)
    })
    return () => { active = false }
  }, [initialBookId, token])

  useEffect(() => {
    if (!token || !selectedBookId) {
      setSpine([])
      setSelectedPageId('')
      setPage(null)
      return
    }
    let active = true
    const requestId = ++requestIdRef.current
    setPageLoading(true)
    setError(null)
    setSpine([])
    setSelectedPageId('')
    setPage(null)
    setMessages([])
    setMessagesPageKey('')
    sessionIdRef.current = null
    closeSocket()
    void getDeepTutorSpine(token, selectedBookId)
      .then((value) => {
        if (!active || requestId !== requestIdRef.current) return
        const nextSpine = deepTutorSpineFromResponse(value).sort((a, b) => a.position - b.position)
        setSpine(nextSpine)
        const preferredPageId = initialPageId && nextSpine.some((item) => item.id === initialPageId)
          ? initialPageId
          : studyStateRef.current.lastOpened?.bookId === selectedBookId
          ? studyStateRef.current.lastOpened.pageId
          : ''
        setSelectedPageId(nextSpine.some((item) => item.id === preferredPageId) ? preferredPageId : nextSpine[0]?.id ?? '')
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : '教材目录加载失败。')
      })
      .finally(() => { if (active) setPageLoading(false) })
    return () => { active = false }
  }, [closeSocket, initialPageId, selectedBookId, token])

  useEffect(() => {
    if (!token || !selectedBookId || !selectedPageId) {
      setPage(null)
      setNoteDraft('')
      return
    }
    let active = true
    const requestId = ++requestIdRef.current
    setPageLoading(true)
    setChatError(null)
    const pageKey = `${selectedBookId}:${selectedPageId}`
    const restoredMessages = studyStateRef.current.chatHistory[pageKey] ?? []
    setMessagesPageKey(pageKey)
    setMessages(restoredMessages)
    sessionIdRef.current = studyStateRef.current.chatSessions[pageKey] ?? null
    closeSocket()
    void getDeepTutorPage(token, selectedBookId, selectedPageId)
      .then((value) => {
        if (!active || requestId !== requestIdRef.current) return
        setPage(deepTutorPageFromResponse(value))
        setNoteDraft(studyStateRef.current.notes[`${selectedBookId}:${selectedPageId}`] ?? '')
        setLastOpened(selectedBookId, selectedPageId)
    })
    .catch((reason: unknown) => {
      if (active) setError(reason instanceof Error ? reason.message : '教材页面加载失败。')
    })
    .finally(() => { if (active) setPageLoading(false) })
    return () => { active = false; closeSocket() }
  }, [closeSocket, selectedBookId, selectedPageId, setLastOpened, token])

  useEffect(() => {
    const pageKey = selectedBookId && selectedPageId ? `${selectedBookId}:${selectedPageId}` : ''
    if (!pageKey || messagesPageKey !== pageKey) return
    setChatHistory(selectedBookId, selectedPageId, messages)
  }, [messages, messagesPageKey, selectedBookId, selectedPageId, setChatHistory])

  const selectBook = (bookId: string) => {
    if (bookId === selectedBookId) return
    setSelectedBookId(bookId)
  }

  const selectPage = (pageId: string) => {
    if (pageId === selectedPageId) return
    setSelectedPageId(pageId)
  }

  const handleCreateBook = async () => {
    if (!token || !topic.trim() || creating) return
    setCreating(true)
    setError(null)
    try {
      const created = await createDeepTutorBook(token, {
        user_intent: topic.trim(),
        language: 'zh',
        knowledge_bases: selectedKnowledgeBase ? [selectedKnowledgeBase] : [],
      })
      const createdBookId = deepTutorBooksFromResponse(created)[0]?.id ?? ''
      const refreshed = studentReadableBooks(await listDeepTutorBooks(token))
      setBooks(refreshed)
      setSelectedBookId(createdBookId || refreshed[0]?.id || '')
      setTopic('')
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : '交互教材创建失败。')
    } finally {
      setCreating(false)
    }
  }

  const handleSaveNote = () => {
    if (!selectedBookId || !selectedPageId) return
    setPageNote(selectedBookId, selectedPageId, noteDraft, {
      bookTitle: selectedBook?.title,
      pageTitle: page?.title,
    })
    setNoteSaved(true)
    window.setTimeout(() => setNoteSaved(false), 1800)
  }

  const handleQuestion = () => {
    if (!question.trim() || chatting || !selectedBookId || !selectedPageId) return
    closeSocket()
    const currentQuestion = question.trim()
    const messageId = `${Date.now()}-${Math.random().toString(36).slice(2)}`
    setQuestion('')
    setChatError(null)
    setChatting(true)
    saveQuestion(selectedBookId, selectedPageId, currentQuestion)
    setMessages((current) => [
      ...current,
      { id: `${messageId}-user`, role: 'user', content: currentQuestion },
      { id: `${messageId}-assistant`, role: 'assistant', content: '' },
    ])

    const socket = new WebSocket(getDeepTutorChatWebSocketUrl())
    socketRef.current = socket
    socket.onopen = () => {
      socket.send(JSON.stringify(buildDeepTutorPageChatMessage(
        currentQuestion,
        selectedBookId,
        selectedPageId,
        sessionIdRef.current,
        selectedKnowledgeBase,
      )))
    }
    socket.onmessage = (event) => {
      let value: unknown = event.data
      try {
        value = JSON.parse(event.data as string) as unknown
      } catch {
        // DeepTutor may emit plain text during a stream.
      }
      if (socketRef.current !== socket) return
      const parsed: DeepTutorChatEvent = parseDeepTutorChatEvent(value)
      if (parsed.sessionId) {
        sessionIdRef.current = parsed.sessionId
        setChatSession(selectedBookId, selectedPageId, parsed.sessionId)
      }
      if (parsed.type === 'error') {
        setChatError(parsed.text || 'DeepTutor 问答失败。')
        setChatting(false)
        return
      }
      if (parsed.text) {
        setMessages((current) => {
          if (current.length === 0) return current
          const next = [...current]
          const last = next.length - 1
          next[last] = { ...next[last], content: next[last].content + parsed.text }
          return next
        })
      }
      if (parsed.type === 'done') setChatting(false)
    }
    socket.onerror = () => {
      if (socketRef.current !== socket) return
      setChatError('无法连接 DeepTutor 问答服务，请检查容器健康状态。')
      setChatting(false)
    }
    socket.onclose = () => {
      if (socketRef.current !== socket) return
      socketRef.current = null
      setChatting(false)
    }
  }

  const nextSpineItem = selectedSpineIndex >= 0 && selectedSpineIndex < spine.length - 1
    ? spine[selectedSpineIndex + 1]
    : null
  const learningRoute = [
    { label: '选择教材', detail: selectedBook ? '教材已就绪' : '从书架开始', state: selectedBook ? 'done' : 'active', Icon: BookOpenCheck },
    { label: '阅读章节', detail: page ? `第 ${selectedSpineIndex + 1} 页` : '等待进入页面', state: page ? 'done' : selectedBook ? 'active' : 'locked', Icon: Layers3 },
    { label: '页面问答', detail: messages.length > 0 ? `${messages.length} 条对话` : '理解关键概念', state: messages.length > 0 ? 'done' : page ? 'active' : 'locked', Icon: MessageCircleQuestion },
    { label: '巩固笔记', detail: noteDraft.trim() ? '已记录要点' : '沉淀学习成果', state: noteDraft.trim() ? 'done' : messages.length > 0 ? 'active' : 'locked', Icon: NotebookPen },
    { label: '完成教材', detail: `${currentProgress}%`, state: currentProgress >= 100 ? 'done' : noteDraft.trim() ? 'active' : 'locked', Icon: Target },
  ]

  return (
    <div className="deep-tutor-cockpit">
      {(error || chatError) && <div role="alert" className="deep-tutor-alert">{error || chatError}</div>}
      <section className="deep-tutor-deck" aria-label="交互教材阅读工作区">
        <aside className="deep-tutor-chapters" aria-label="教材章节目录">
          <div className="deep-tutor-book-summary">
            <div className="deep-tutor-book-mark"><BookOpenCheck /></div>
            <div className="min-w-0"><strong>{selectedBook?.title ?? '选择交互教材'}</strong><span>{spine.length > 0 ? `学习进度 ${currentProgress}%` : '从书架选择一本教材'}</span></div>
          </div>
          <div className="deep-tutor-progress" aria-label={`教材完成度 ${currentProgress}%`}><span style={{ width: `${currentProgress}%` }} /></div>
          <label className="deep-tutor-book-search"><Search aria-hidden="true" /><input value={bookFilter} onChange={(event) => setBookFilter(event.target.value)} placeholder="搜索教材" aria-label="搜索教材" /></label>
          <div className="deep-tutor-book-tabs" aria-label="教材书架">
            {filteredBooks.map((book) => <button key={book.id} type="button" data-active={selectedBookId === book.id} onClick={() => selectBook(book.id)}><Layers3 /><span><strong>{book.title}</strong><small>{completedForBook(book.id).length} 页已完成</small></span></button>)}
            {!loading && filteredBooks.length === 0 && <p>暂无匹配教材，可在下方创建主题教材。</p>}
            {loading && <div className="deep-tutor-loading"><LoaderCircle />同步书架中</div>}
          </div>
          <div className="deep-tutor-chapter-heading"><span>章节目录</span><small>{currentCompletedPages.length}/{spine.length || 0}</small></div>
          <nav className="deep-tutor-spine" aria-label="当前教材章节">
            {spine.map((item, index) => {
              const completed = isPageCompleted(selectedBookId, item.id)
              return <button key={item.id} type="button" data-active={selectedPageId === item.id} data-complete={completed} onClick={() => selectPage(item.id)}><span>{completed ? <Check /> : index + 1}</span><strong>{item.title}</strong></button>
            })}
          </nav>
          <details className="deep-tutor-create">
            <summary><Plus />创建主题教材</summary>
            <div>
              <input value={topic} onChange={(event) => setTopic(event.target.value)} placeholder="输入学习主题" aria-label="教材主题" />
              <label><Database /><select value={selectedKnowledgeBase} onChange={(event) => setSelectedKnowledgeBase(event.target.value)} aria-label="选择知识库"><option value="">不指定知识库</option>{knowledgeBases.map((base) => <option key={base.name} value={base.name}>{base.name}</option>)}</select></label>
              <button type="button" onClick={() => { void handleCreateBook() }} disabled={!topic.trim() || creating || !token}>{creating ? <LoaderCircle className="animate-spin" /> : <Plus />}{creating ? '正在创建' : '创建教材'}</button>
            </div>
          </details>
        </aside>
        <main className="deep-tutor-reader">
          <header className="deep-tutor-reader-titlebar">
            <div><span><ChevronLeft />{selectedBook?.title ?? '交互教材'}</span><h2>{selectedSpineItem ? `第 ${selectedSpineIndex + 1} 节 · ${selectedSpineItem.title}` : '请选择阅读章节'}</h2></div>
            {pageLoading && <LoaderCircle className="animate-spin" />}
            {page && <button type="button" onClick={() => markPageCompleted(selectedBookId, page.id)} disabled={isPageCompleted(selectedBookId, page.id)}><Bookmark />{isPageCompleted(selectedBookId, page.id) ? '已完成' : '标记完成'}</button>}
          </header>
          {page ? (
            <article className="deep-reader-book">
              <div className="deep-reader-pages">
                <div className="deep-reader-page-heading"><span>{selectedSpineIndex + 1}.{Math.max(page.blocks.length, 1)}</span><h3>{page.title}</h3><small>交互阅读 · 页面内容来自当前教材</small></div>
                <div className="deep-reader-content">
                  {page.blocks.length > 0 ? page.blocks.map((block) => <div key={block.id} id={`deeptutor-block-${block.id}`} className="deep-reader-block-wrap"><BookBlock block={block} /></div>) : <div className="deep-reader-markdown prose prose-sm max-w-none"><ReactMarkdown>{page.content}</ReactMarkdown></div>}
                </div>
                <div className="deep-reader-note"><div><NotebookPen /><span>随堂笔记</span></div><textarea value={noteDraft} onChange={(event) => setNoteDraft(event.target.value)} placeholder="记录本页最重要的概念或疑问…" rows={2} aria-label="本页学习笔记" /><button type="button" onClick={handleSaveNote} disabled={!pageNoteKey}>{noteSaved ? <Check /> : <NotebookPen />}{noteSaved ? '已保存' : '保存笔记'}</button></div>
              </div>
              <footer className="deep-reader-controls">
                <button type="button" onClick={() => selectedSpineIndex > 0 && selectPage(spine[selectedSpineIndex - 1].id)} disabled={selectedSpineIndex <= 0}><ChevronLeft />上一节</button>
                <div aria-label="本书页面进度">{spine.map((item) => <span key={item.id} data-active={item.id === selectedPageId} data-complete={isPageCompleted(selectedBookId, item.id)} />)}</div>
                <button type="button" onClick={() => nextSpineItem && selectPage(nextSpineItem.id)} disabled={!nextSpineItem}>下一节<ChevronRight /></button>
              </footer>
            </article>
          ) : <div className="deep-reader-empty">{pageLoading ? <LoaderCircle className="animate-spin" /> : <BookOpenCheck />}<strong>{selectedBook ? '正在准备教材页面' : '从左侧选择一本教材'}</strong><span>选择章节后，内容、笔记和 AI 问答会在同一工作区联动。</span></div>}
        </main>
        <aside className="deep-tutor-ai" aria-label="AI 页面问答">
          <header><div><MessageCircleQuestion /><span><strong>AI 问答</strong><small>基于当前教材页面</small></span></div>{messages.length > 0 && <button type="button" onClick={() => { clearChatHistory(selectedBookId, selectedPageId); setMessages([]); sessionIdRef.current = null }}>清空</button>}</header>
          <div className="deep-tutor-ai-intro"><div><Sparkles /></div><p>{page ? `我已阅读“${page.title}”，可以继续追问。` : '选择页面后，我会带入教材上下文。'}</p></div>
          <div className="deep-tutor-messages" aria-live="polite">
            {messages.length === 0 && <div className="deep-tutor-message-empty"><Lightbulb /><span>试着问：请用一个生活中的例子解释本页核心概念。</span></div>}
            {messages.map((message) => <div key={message.id} className="deep-tutor-message" data-role={message.role}>{message.content || (chatting && message.role === 'assistant' ? <span><LoaderCircle className="animate-spin" />正在生成回答…</span> : '暂无回复')}{message.role === 'user' && <small><Bookmark />已加入待复习问题</small>}</div>)}
          </div>
          <div className="deep-tutor-suggestions"><button type="button" disabled={!page || chatting} onClick={() => setQuestion('请举一个例子帮助我理解本页核心概念')}>举个例子</button><button type="button" disabled={!page || chatting} onClick={() => setQuestion('请换一个更简单的角度解释本页内容')}>换个角度解释</button></div>
          <div className="deep-tutor-question-box"><textarea value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); handleQuestion() } }} placeholder={selectedBook ? '继续提问…' : '先选择教材'} rows={2} aria-label="向当前教材提问" disabled={!selectedBook || !selectedPageId || chatting} /><button type="button" onClick={handleQuestion} aria-label="发送问题" disabled={!selectedBook || !selectedPageId || !question.trim() || chatting}>{chatting ? <LoaderCircle className="animate-spin" /> : <Send />}</button></div>
        </aside>
      </section>
      <section className="deep-tutor-route" aria-label="今日学习航线">
        <div className="deep-tutor-route-title"><Target /><span><strong>今日学习航线</strong><small>跟随教材完成理解闭环</small></span></div>
        <ol>{learningRoute.map(({ label, detail, state: stepState, Icon }) => <li key={label} data-state={stepState}><span><Icon /></span><div><strong>{label}</strong><small>{detail}</small></div></li>)}</ol>
        <button type="button" disabled={!page} onClick={() => { if (nextSpineItem) selectPage(nextSpineItem.id); else if (page && !isPageCompleted(selectedBookId, page.id)) markPageCompleted(selectedBookId, page.id) }}><span><small>当前任务</small><strong>{nextSpineItem ? '进入下一节' : currentProgress >= 100 ? '教材已完成' : '完成当前页'}</strong></span><ChevronRight /></button>
      </section>
    </div>
  )
}
