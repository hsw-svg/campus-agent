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
import useDeepTutorStudyState from '../hooks/useDeepTutorStudyState'

interface DeepTutorBookPanelProps {
  token: string | null
  initialBookId?: string
}

interface TutorMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
}

function newSessionId(): string {
  return `campus-agent-${Date.now()}-${Math.random().toString(36).slice(2)}`
}

function blockTone(type: string): { label: string; className: string; Icon: typeof Lightbulb } {
  if (['callout', 'tip', 'hint', 'highlight'].some((item) => type.includes(item))) {
    return { label: '学习提示', className: 'border-tertiary/30 bg-tertiary-container/45', Icon: Lightbulb }
  }
  if (['quiz', 'question', 'exercise', 'practice'].some((item) => type.includes(item))) {
    return { label: '练习一下', className: 'border-secondary/30 bg-secondary-container/25', Icon: Target }
  }
  return { label: '知识内容', className: 'border-outline-variant/60 bg-surface-container', Icon: FileText }
}

function BookBlock({ block }: { block: DeepTutorBlock }) {
  const tone = blockTone(block.type)
  const Icon = tone.Icon
  return (
    <div className={`rounded-2xl border p-4 sm:p-5 ${tone.className}`}>
      <div className="mb-3 flex items-center gap-2 text-xs font-black text-on-surface-variant">
        <Icon className="h-4 w-4 text-secondary" />
        <span>{block.title || tone.label}</span>
      </div>
      <div className="prose prose-sm max-w-none text-on-surface prose-headings:text-on-surface prose-p:text-on-surface-variant prose-strong:text-on-surface prose-li:text-on-surface-variant">
        <ReactMarkdown>{block.content || '本内容块暂时没有可显示的文字。'}</ReactMarkdown>
      </div>
    </div>
  )
}

export default function DeepTutorBookPanel({ token, initialBookId }: DeepTutorBookPanelProps) {
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
  const [noteDraft, setNoteDraft] = useState('')
  const [noteSaved, setNoteSaved] = useState(false)
  const [loading, setLoading] = useState(true)
  const [pageLoading, setPageLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [chatting, setChatting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [chatError, setChatError] = useState<string | null>(null)
  const socketRef = useRef<WebSocket | null>(null)
  const sessionIdRef = useRef(newSessionId())
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
        const nextBooks = deepTutorBooksFromResponse(booksResult.value)
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
    closeSocket()
    void getDeepTutorSpine(token, selectedBookId)
      .then((value) => {
        if (!active || requestId !== requestIdRef.current) return
        const nextSpine = deepTutorSpineFromResponse(value).sort((a, b) => a.position - b.position)
        setSpine(nextSpine)
        const lastOpenedPage = studyStateRef.current.lastOpened?.bookId === selectedBookId
          ? studyStateRef.current.lastOpened.pageId
          : ''
        setSelectedPageId(nextSpine.some((item) => item.id === lastOpenedPage) ? lastOpenedPage : nextSpine[0]?.id ?? '')
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : '教材目录加载失败。')
      })
      .finally(() => { if (active) setPageLoading(false) })
    return () => { active = false }
  }, [closeSocket, selectedBookId, token])

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
    setMessages([])
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
    return () => { active = false }
  }, [closeSocket, selectedBookId, selectedPageId, setLastOpened, token])

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
      await createDeepTutorBook(token, {
        user_intent: topic.trim(),
        language: 'zh',
        knowledge_bases: selectedKnowledgeBase ? [selectedKnowledgeBase] : [],
      })
      const refreshed = deepTutorBooksFromResponse(await listDeepTutorBooks(token))
      setBooks(refreshed)
      setSelectedBookId((current) => current || refreshed[0]?.id || '')
      setTopic('')
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : '交互教材创建失败。')
    } finally {
      setCreating(false)
    }
  }

  const handleSaveNote = () => {
    if (!selectedBookId || !selectedPageId) return
    setPageNote(selectedBookId, selectedPageId, noteDraft)
    setNoteSaved(true)
    window.setTimeout(() => setNoteSaved(false), 1800)
  }

  const handleQuestion = () => {
    if (!question.trim() || chatting || !selectedBookId) return
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
      socket.send(JSON.stringify({
        language: 'zh',
        message: currentQuestion,
        session_id: sessionIdRef.current,
        kb_name: selectedKnowledgeBase || null,
        enable_rag: true,
        book_id: selectedBookId,
        page_id: selectedPageId || null,
      }))
    }
    socket.onmessage = (event) => {
      let value: unknown = event.data
      try {
        value = JSON.parse(event.data as string) as unknown
      } catch {
        // DeepTutor may emit plain text during a stream.
      }
      const parsed: DeepTutorChatEvent = parseDeepTutorChatEvent(value)
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
      if (['result', 'done', 'complete'].includes(parsed.type)) setChatting(false)
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

  return (
    <div className="w-full space-y-5 py-4 sm:py-8">
      <section className="rounded-3xl border border-secondary/20 bg-secondary-container/10 p-5 sm:p-7">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <div className="mb-2 flex items-center gap-2 text-secondary">
              <BookOpenCheck className="h-5 w-5" />
              <span className="text-[11px] font-black uppercase tracking-[0.2em]">DeepTutor Interactive Books</span>
            </div>
            <h2 className="text-2xl font-black text-on-surface sm:text-3xl">交互式教材，边读边问边练</h2>
            <p className="mt-2 text-sm font-medium leading-6 text-on-surface-variant">像翻阅一门会回应你的课程：从目录进入页面，在重点和练习卡片之间阅读，并让页面问答围绕当前上下文继续解释。</p>
          </div>
          <div className="flex items-center gap-2 rounded-2xl border border-outline-variant/60 bg-surface-container-lowest px-3 py-2 text-xs font-bold text-on-surface-variant">
            <Sparkles className="h-4 w-4 text-secondary" />
            当前应用安全代理问答
          </div>
        </div>
      </section>

      {error && <div role="alert" className="rounded-2xl border border-error/30 bg-error-container px-4 py-3 text-sm font-semibold text-on-error-container">{error}</div>}
      {chatError && <div role="alert" className="rounded-2xl border border-error/30 bg-error-container px-4 py-3 text-sm font-semibold text-on-error-container">{chatError}</div>}

      <section className="grid gap-3 sm:grid-cols-3">
        {[
          { label: '书本', value: books.length, Icon: BookOpenCheck },
          { label: '当前阅读进度', value: `${currentProgress}%`, Icon: CheckCircle2 },
          { label: '待复习问题', value: selectedBookId ? '已收录' : '—', Icon: Bookmark },
        ].map(({ label, value, Icon }) => (
          <div key={label} className="flex items-center gap-3 rounded-2xl border border-outline-variant/60 bg-surface-container-lowest p-4">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-secondary-container/50 text-secondary"><Icon className="h-5 w-5" /></span>
            <div><p className="text-xl font-black text-on-surface">{value}</p><p className="text-xs font-bold text-on-surface-variant">{label}</p></div>
          </div>
        ))}
      </section>

      <section className="grid gap-5 xl:grid-cols-[17rem_minmax(0,1fr)_22rem]">
        <aside className="rounded-2xl border border-outline-variant/60 bg-surface-container-lowest p-4">
          <div className="mb-4 flex items-center justify-between gap-2">
            <div>
              <p className="text-[10px] font-black uppercase tracking-[0.18em] text-secondary">My library</p>
              <h3 className="mt-1 text-sm font-black text-on-surface">我的交互书本</h3>
            </div>
            {loading && <LoaderCircle className="h-4 w-4 animate-spin text-secondary" />}
          </div>
          <label className="mb-3 flex items-center gap-2 rounded-xl border border-outline-variant/60 bg-surface px-3 py-2 text-xs text-on-surface-variant focus-within:border-secondary">
            <Search className="h-4 w-4 shrink-0" />
            <input value={bookFilter} onChange={(event) => setBookFilter(event.target.value)} placeholder="搜索书本" className="min-w-0 flex-1 bg-transparent outline-none" />
          </label>
          <div className="space-y-2">
            {filteredBooks.map((book) => {
              const completed = completedForBook(book.id).length
              return (
                <button key={book.id} type="button" onClick={() => { selectBook(book.id) }} className={`w-full rounded-xl border px-3 py-3 text-left transition ${selectedBookId === book.id ? 'border-secondary bg-secondary-container/20 text-secondary' : 'border-outline-variant/50 text-on-surface hover:border-secondary/50'}`}>
                  <div className="flex items-start gap-2">
                    <Layers3 className="mt-0.5 h-4 w-4 shrink-0" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-xs font-black">{book.title}</p>
                      <p className="mt-1 line-clamp-2 text-[11px] leading-5 text-on-surface-variant">{book.description}</p>
                    </div>
                  </div>
                  <div className="mt-3 flex items-center justify-between text-[10px] font-bold text-outline"><span>{(book.pageCount ?? spine.length) || '—'} 页面</span><span className={selectedBookId === book.id ? 'text-secondary' : ''}>{completed} 已完成</span></div>
                </button>
              )
            })}
            {!loading && filteredBooks.length === 0 && <p className="rounded-xl bg-surface-container px-3 py-5 text-xs leading-5 text-on-surface-variant">还没有匹配的书本，可在页面下方创建一本主题教材。</p>}
          </div>
        </aside>

        <main className="min-w-0 rounded-2xl border border-outline-variant/60 bg-surface-container-lowest p-4 sm:p-6">
          <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.18em] text-secondary"><BookOpenCheck className="h-3.5 w-3.5" /> Reading room</div>
              <h3 className="mt-2 truncate text-xl font-black text-on-surface">{selectedBook?.title ?? '选择一本交互教材'}</h3>
              {selectedSpineItem && <p className="mt-1 text-xs font-semibold text-on-surface-variant">第 {selectedSpineIndex + 1} 节 · {selectedSpineItem.title}</p>}
            </div>
            {pageLoading && <LoaderCircle className="h-5 w-5 animate-spin text-secondary" />}
          </div>

          {spine.length > 0 && (
            <div className="mb-5 rounded-xl border border-outline-variant/50 bg-surface-container p-3">
              <div className="mb-2 flex items-center justify-between text-[11px] font-bold text-on-surface-variant"><span>阅读进度</span><span>{currentCompletedPages.length}/{spine.length} 页面</span></div>
              <div className="h-2 overflow-hidden rounded-full bg-surface-container-high"><div className="h-full rounded-full bg-secondary transition-all" style={{ width: `${currentProgress}%` }} /></div>
              <div className="mt-3 flex gap-1 overflow-x-auto pb-1">
                {spine.map((item, index) => (
                  <button key={item.id} type="button" title={item.title} onClick={() => selectPage(item.id)} className={`flex h-7 min-w-7 items-center justify-center rounded-lg px-2 text-[10px] font-black transition ${selectedPageId === item.id ? 'bg-secondary text-on-secondary' : isPageCompleted(selectedBookId, item.id) ? 'bg-tertiary-container text-on-tertiary-container' : 'bg-surface-container-high text-on-surface-variant hover:bg-secondary-container'}`}>{isPageCompleted(selectedBookId, item.id) ? <Check className="h-3.5 w-3.5" /> : index + 1}</button>
                ))}
              </div>
            </div>
          )}

          {page ? (
            <article>
              <div className="mb-5 flex items-start justify-between gap-3 border-b border-outline-variant/50 pb-4">
                <div><p className="text-[10px] font-black uppercase tracking-[0.18em] text-secondary">当前页面</p><h4 className="mt-1 text-2xl font-black text-on-surface">{page.title}</h4></div>
                {isPageCompleted(selectedBookId, page.id) && <span className="inline-flex items-center gap-1 rounded-full bg-tertiary-container px-2.5 py-1 text-[10px] font-black text-on-tertiary-container"><CheckCircle2 className="h-3.5 w-3.5" /> 已完成</span>}
              </div>
              <div className="space-y-4">
                {page.blocks.length > 0 ? page.blocks.map((block) => <BookBlock key={block.id} block={block} />) : <div className="prose prose-sm max-w-none text-on-surface prose-headings:text-on-surface prose-p:text-on-surface-variant prose-strong:text-on-surface"><ReactMarkdown>{page.content}</ReactMarkdown></div>}
              </div>

              <div className="mt-6 rounded-2xl border border-outline-variant/60 bg-surface-container p-4">
                <div className="mb-2 flex items-center gap-2"><NotebookPen className="h-4 w-4 text-secondary" /><span className="text-xs font-black text-on-surface">我的学习笔记</span></div>
                <textarea value={noteDraft} onChange={(event) => setNoteDraft(event.target.value)} placeholder="写下本页最重要的一个概念或疑问…" rows={3} className="w-full resize-none rounded-xl border border-outline-variant/60 bg-surface-container-lowest px-3 py-2 text-xs leading-5 outline-none focus:border-secondary" />
                <div className="mt-2 flex justify-end"><button type="button" onClick={handleSaveNote} disabled={!pageNoteKey} className="inline-flex items-center gap-1.5 rounded-lg bg-secondary px-3 py-2 text-xs font-black text-on-secondary disabled:opacity-50">{noteSaved ? <Check className="h-3.5 w-3.5" /> : <NotebookPen className="h-3.5 w-3.5" />}{noteSaved ? '已保存' : '保存笔记'}</button></div>
              </div>

              <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
                <button type="button" onClick={() => selectedSpineIndex > 0 && selectPage(spine[selectedSpineIndex - 1].id)} disabled={selectedSpineIndex <= 0} className="inline-flex items-center gap-1.5 rounded-xl border border-outline-variant/60 px-3 py-2 text-xs font-black text-on-surface-variant disabled:cursor-not-allowed disabled:opacity-40"><ChevronLeft className="h-4 w-4" /> 上一页</button>
                <button type="button" onClick={() => markPageCompleted(selectedBookId, page.id)} disabled={isPageCompleted(selectedBookId, page.id)} className="inline-flex items-center gap-1.5 rounded-xl border border-tertiary/40 bg-tertiary-container/40 px-3 py-2 text-xs font-black text-on-tertiary-container disabled:cursor-default disabled:opacity-60"><CheckCircle2 className="h-4 w-4" /> {isPageCompleted(selectedBookId, page.id) ? '本页已完成' : '标记本页完成'}</button>
                <button type="button" onClick={() => selectedSpineIndex >= 0 && selectedSpineIndex < spine.length - 1 && selectPage(spine[selectedSpineIndex + 1].id)} disabled={selectedSpineIndex < 0 || selectedSpineIndex >= spine.length - 1} className="inline-flex items-center gap-1.5 rounded-xl bg-secondary px-3 py-2 text-xs font-black text-on-secondary disabled:cursor-not-allowed disabled:opacity-40">下一页 <ChevronRight className="h-4 w-4" /></button>
              </div>
            </article>
          ) : (
            <div className="flex min-h-[28rem] items-center justify-center rounded-2xl border border-dashed border-outline-variant/70 bg-surface-container px-6 text-center text-sm font-semibold text-on-surface-variant">{selectedBook ? (pageLoading ? '正在打开页面…' : '这本教材暂时没有可展示的页面。') : '从左侧书架选择一本教材开始阅读。'}</div>
          )}
        </main>

        <aside className="flex min-h-[34rem] flex-col rounded-2xl border border-outline-variant/60 bg-surface-container-lowest p-4">
          <div className="mb-3 flex items-start justify-between gap-2">
            <div className="flex items-center gap-2"><MessageCircleQuestion className="h-5 w-5 text-secondary" /><div><h3 className="text-sm font-black text-on-surface">页面问答</h3><p className="text-[11px] font-semibold text-on-surface-variant">围绕当前页面继续追问</p></div></div>
            {messages.length > 0 && <button type="button" onClick={() => setMessages([])} className="text-[10px] font-bold text-outline hover:text-secondary">清空</button>}
          </div>
          <div className="mb-3 rounded-xl bg-secondary-container/15 px-3 py-2 text-[11px] leading-5 text-on-surface-variant">{page ? `问答上下文：${page.title}` : '选择页面后，DeepTutor 会带入页面上下文。'}</div>
          <div className="flex-1 space-y-3 overflow-y-auto rounded-xl bg-surface-container p-3">
            {messages.length === 0 && <div className="py-10 text-center"><MessageCircleQuestion className="mx-auto h-7 w-7 text-secondary/60" /><p className="mt-3 text-xs leading-5 text-on-surface-variant">例如：请用一个生活中的例子解释本页的核心概念。</p></div>}
            {messages.map((message) => (
              <div key={message.id} className={`rounded-xl px-3 py-2 text-xs leading-5 ${message.role === 'user' ? 'ml-5 bg-secondary text-on-secondary' : 'mr-5 bg-surface-container-lowest text-on-surface'}`}>
                {message.content || (chatting && message.role === 'assistant' ? <span className="inline-flex items-center gap-1.5 text-on-surface-variant"><LoaderCircle className="h-3.5 w-3.5 animate-spin" />正在思考…</span> : '暂无回复')}
                {message.role === 'user' && <div className="mt-1 flex items-center gap-1 text-[10px] font-bold text-on-secondary/70"><Bookmark className="h-3 w-3" />已加入待复习问题</div>}
              </div>
            ))}
          </div>
          <div className="mt-3 space-y-2">
            <textarea value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); handleQuestion() } }} placeholder={selectedBook ? '向当前教材提问…' : '先选择教材'} rows={3} className="w-full resize-none rounded-xl border border-outline-variant/60 bg-surface px-3 py-2 text-xs outline-none transition-colors focus:border-secondary" disabled={!selectedBook || !selectedPageId || chatting} />
            <button type="button" onClick={handleQuestion} disabled={!selectedBook || !selectedPageId || !question.trim() || chatting} className="flex w-full items-center justify-center gap-2 rounded-xl bg-secondary px-3 py-2.5 text-xs font-black text-on-secondary disabled:cursor-not-allowed disabled:opacity-50">{chatting ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}{chatting ? 'DeepTutor 正在回答' : '发送并收藏问题'}</button>
          </div>
        </aside>
      </section>

      <section className="rounded-2xl border border-outline-variant/60 bg-surface-container-lowest p-4 sm:p-5">
        <div className="mb-3 flex items-center gap-2"><Plus className="h-4 w-4 text-secondary" /><div><h3 className="text-sm font-black text-on-surface">现场准备：创建一本主题教材</h3><p className="text-[11px] font-semibold text-on-surface-variant">建议提前生成主要书本，演示时重点展示阅读和页面问答。</p></div></div>
        <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_16rem_auto]">
          <input value={topic} onChange={(event) => setTopic(event.target.value)} placeholder="例如：Python 高阶函数与装饰器" className="rounded-xl border border-outline-variant/60 bg-surface px-3 py-2.5 text-xs outline-none focus:border-secondary" />
          <label className="flex items-center gap-2 rounded-xl border border-outline-variant/60 bg-surface px-3 py-2.5 text-xs text-on-surface-variant"><Database className="h-4 w-4 shrink-0 text-secondary" /><select value={selectedKnowledgeBase} onChange={(event) => setSelectedKnowledgeBase(event.target.value)} className="min-w-0 flex-1 bg-transparent outline-none"><option value="">不指定知识库</option>{knowledgeBases.map((base) => <option key={base.name} value={base.name}>{base.name}</option>)}</select></label>
          <button type="button" onClick={() => { void handleCreateBook() }} disabled={!topic.trim() || creating || !token} className="inline-flex items-center justify-center gap-2 rounded-xl bg-secondary px-4 py-2.5 text-xs font-black text-on-secondary disabled:opacity-50">{creating ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}{creating ? '正在创建' : '创建教材'}</button>
        </div>
        <div className="mt-3 flex items-center gap-2 text-[11px] font-semibold text-on-surface-variant"><ArrowLeft className="h-3.5 w-3.5 text-secondary" />创建完成后会自动刷新书架，页面问答仍通过当前应用代理。</div>
      </section>
    </div>
  )
}
