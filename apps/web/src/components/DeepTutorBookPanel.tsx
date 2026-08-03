import { useEffect, useMemo, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import {
  BookOpenCheck,
  ChevronRight,
  Database,
  LoaderCircle,
  MessageCircleQuestion,
  Plus,
  Send,
  Sparkles,
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
  type DeepTutorBook,
  type DeepTutorChatEvent,
  type DeepTutorKnowledgeBase,
  type DeepTutorPage,
  type DeepTutorSpineItem,
} from '../api'

interface DeepTutorBookPanelProps {
  token: string | null
}

interface TutorMessage {
  role: 'user' | 'assistant'
  content: string
}

function newSessionId(): string {
  return `campus-agent-${Date.now()}-${Math.random().toString(36).slice(2)}`
}

export default function DeepTutorBookPanel({ token }: DeepTutorBookPanelProps) {
  const [books, setBooks] = useState<DeepTutorBook[]>([])
  const [knowledgeBases, setKnowledgeBases] = useState<DeepTutorKnowledgeBase[]>([])
  const [selectedBookId, setSelectedBookId] = useState('')
  const [spine, setSpine] = useState<DeepTutorSpineItem[]>([])
  const [selectedPageId, setSelectedPageId] = useState('')
  const [page, setPage] = useState<DeepTutorPage | null>(null)
  const [topic, setTopic] = useState('')
  const [selectedKnowledgeBase, setSelectedKnowledgeBase] = useState('')
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState<TutorMessage[]>([])
  const [loading, setLoading] = useState(true)
  const [pageLoading, setPageLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [chatting, setChatting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [chatError, setChatError] = useState<string | null>(null)
  const socketRef = useRef<WebSocket | null>(null)
  const sessionIdRef = useRef(newSessionId())

  const selectedBook = useMemo(
    () => books.find((book) => book.id === selectedBookId) ?? null,
    [books, selectedBookId],
  )
  const selectedSpineItem = useMemo(
    () => spine.find((item) => item.id === selectedPageId) ?? null,
    [selectedPageId, spine],
  )

  useEffect(() => {
    if (!token) {
      setLoading(false)
      setError('当前学生工作空间尚未建立，暂时无法打开交互教材。')
      return
    }
    let active = true
    setLoading(true)
    setError(null)
    void Promise.allSettled([
      listDeepTutorBooks(token),
      listDeepTutorKnowledgeBases(token),
    ]).then((results) => {
      if (!active) return
      const [booksResult, knowledgeResult] = results
      if (booksResult.status === 'fulfilled') {
        const nextBooks = deepTutorBooksFromResponse(booksResult.value)
        setBooks(nextBooks)
        setSelectedBookId((current) => current && nextBooks.some((book) => book.id === current)
          ? current
          : nextBooks[0]?.id ?? '')
      } else {
        setError(booksResult.reason instanceof Error ? booksResult.reason.message : '交互教材加载失败。')
      }
      if (knowledgeResult.status === 'fulfilled') {
        setKnowledgeBases(deepTutorKnowledgeBasesFromResponse(knowledgeResult.value))
      }
      setLoading(false)
    })
    return () => { active = false }
  }, [token])

  useEffect(() => {
    if (!token || !selectedBookId) {
      setSpine([])
      setSelectedPageId('')
      setPage(null)
      return
    }
    let active = true
    setPageLoading(true)
    setError(null)
    void getDeepTutorSpine(token, selectedBookId)
      .then((value) => {
        if (!active) return
        const nextSpine = deepTutorSpineFromResponse(value).sort((a, b) => a.position - b.position)
        setSpine(nextSpine)
        setSelectedPageId(nextSpine[0]?.id ?? '')
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : '教材目录加载失败。')
      })
      .finally(() => { if (active) setPageLoading(false) })
    return () => { active = false }
  }, [selectedBookId, token])

  useEffect(() => {
    if (!token || !selectedBookId || !selectedPageId) {
      setPage(null)
      return
    }
    let active = true
    setPageLoading(true)
    void getDeepTutorPage(token, selectedBookId, selectedPageId)
      .then((value) => {
        if (active) setPage(deepTutorPageFromResponse(value))
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : '教材页面加载失败。')
      })
      .finally(() => { if (active) setPageLoading(false) })
    return () => { active = false }
  }, [selectedBookId, selectedPageId, token])

  useEffect(() => () => {
    socketRef.current?.close()
  }, [])

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
      const createdBook = deepTutorBooksFromResponse({ books: [created] })[0]
      const nextBooks = await listDeepTutorBooks(token)
      const refreshedBooks = deepTutorBooksFromResponse(nextBooks)
      setBooks(refreshedBooks)
      setSelectedBookId(createdBook?.id ?? refreshedBooks[0]?.id ?? '')
      setTopic('')
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : '交互教材创建失败。')
    } finally {
      setCreating(false)
    }
  }

  const handleQuestion = () => {
    if (!question.trim() || chatting || !selectedBookId) return
    socketRef.current?.close()
    const currentQuestion = question.trim()
    setQuestion('')
    setChatError(null)
    setChatting(true)
    setMessages((current) => [
      ...current,
      { role: 'user', content: currentQuestion },
      { role: 'assistant', content: '' },
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
        // DeepTutor can emit plain text during a stream.
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
      setChatError('无法连接 DeepTutor 问答服务，请检查容器健康状态。')
      setChatting(false)
    }
    socket.onclose = () => {
      setChatting(false)
      if (socketRef.current === socket) socketRef.current = null
    }
  }

  return (
    <div className="w-full space-y-5 py-4 sm:py-8">
      <div className="flex flex-col gap-4 rounded-3xl border border-secondary/20 bg-secondary-container/10 p-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="mb-2 flex items-center gap-2 text-secondary">
            <BookOpenCheck className="h-5 w-5" />
            <span className="text-[11px] font-black uppercase tracking-[0.2em]">DeepTutor Interactive Books</span>
          </div>
          <h2 className="text-2xl font-black text-on-surface">交互式教材与页面问答</h2>
          <p className="mt-2 max-w-2xl text-sm font-medium leading-6 text-on-surface-variant">选择已准备好的课程书本，按页面阅读并提问。比赛演示前建议提前生成主要书本，现场只做阅读和问答。</p>
        </div>
        <div className="flex items-center gap-2 rounded-2xl border border-outline-variant/60 bg-surface-container-lowest px-3 py-2 text-xs font-bold text-on-surface-variant">
          <Sparkles className="h-4 w-4 text-secondary" />
          浏览器只访问当前应用
        </div>
      </div>

      {error && <div role="alert" className="rounded-2xl border border-error/30 bg-error-container px-4 py-3 text-sm font-semibold text-on-error-container">{error}</div>}
      {chatError && <div role="alert" className="rounded-2xl border border-error/30 bg-error-container px-4 py-3 text-sm font-semibold text-on-error-container">{chatError}</div>}

      <div className="grid gap-5 xl:grid-cols-[17rem_minmax(0,1fr)_23rem]">
        <aside className="rounded-2xl border border-outline-variant/60 bg-surface-container-lowest p-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-black text-on-surface">我的交互教材</h3>
            {loading && <LoaderCircle className="h-4 w-4 animate-spin text-secondary" />}
          </div>
          <div className="space-y-2">
            {books.map((book) => (
              <button
                type="button"
                key={book.id}
                onClick={() => { setSelectedBookId(book.id); setMessages([]) }}
                className={`w-full rounded-xl border px-3 py-3 text-left transition-colors ${selectedBookId === book.id ? 'border-secondary bg-secondary-container/20 text-secondary' : 'border-outline-variant/50 text-on-surface hover:border-secondary/50'}`}
              >
                <p className="truncate text-xs font-black">{book.title}</p>
                <p className="mt-1 line-clamp-2 text-[11px] leading-5 text-on-surface-variant">{book.description}</p>
              </button>
            ))}
            {!loading && books.length === 0 && <p className="rounded-xl bg-surface-container px-3 py-4 text-xs leading-5 text-on-surface-variant">还没有可用书本，可在右侧输入主题生成一本。</p>}
          </div>
        </aside>

        <section className="min-w-0 rounded-2xl border border-outline-variant/60 bg-surface-container-lowest p-5">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-[10px] font-black uppercase tracking-[0.18em] text-secondary">当前页面</p>
              <h3 className="mt-1 text-xl font-black text-on-surface">{selectedBook?.title ?? '选择一本交互教材'}</h3>
            </div>
            {pageLoading && <LoaderCircle className="h-5 w-5 animate-spin text-secondary" />}
          </div>

          {spine.length > 0 && (
            <div className="mb-5 flex gap-2 overflow-x-auto pb-1">
              {spine.map((item) => (
                <button
                  type="button"
                  key={item.id}
                  onClick={() => setSelectedPageId(item.id)}
                  className={`flex shrink-0 items-center gap-1 rounded-full border px-3 py-2 text-[11px] font-bold ${selectedPageId === item.id ? 'border-secondary bg-secondary text-on-secondary' : 'border-outline-variant/60 text-on-surface-variant hover:border-secondary/50'}`}
                >
                  {item.title}<ChevronRight className="h-3 w-3" />
                </button>
              ))}
            </div>
          )}

          {page ? (
            <article className="prose prose-sm max-w-none text-on-surface prose-headings:text-on-surface prose-p:text-on-surface-variant prose-strong:text-on-surface">
              <h4>{page.title}</h4>
              <ReactMarkdown>{page.content}</ReactMarkdown>
            </article>
          ) : (
            <div className="flex min-h-64 items-center justify-center rounded-2xl border border-dashed border-outline-variant/70 bg-surface-container px-6 text-center text-sm font-semibold text-on-surface-variant">
              {selectedBook ? '这本教材暂时没有可展示的页面。' : '从左侧选择一本教材开始。'}
            </div>
          )}
          {selectedSpineItem && <p className="mt-5 text-[11px] font-semibold text-outline">页面上下文：{selectedSpineItem.title}</p>}
        </section>

        <aside className="flex min-h-[32rem] flex-col rounded-2xl border border-outline-variant/60 bg-surface-container-lowest p-4">
          <div className="mb-3 flex items-center gap-2">
            <MessageCircleQuestion className="h-5 w-5 text-secondary" />
            <div>
              <h3 className="text-sm font-black text-on-surface">页面问答</h3>
              <p className="text-[11px] font-semibold text-on-surface-variant">围绕当前页面继续追问</p>
            </div>
          </div>
          <div className="flex-1 space-y-3 overflow-y-auto rounded-xl bg-surface-container p-3">
            {messages.length === 0 && <p className="py-8 text-center text-xs leading-5 text-on-surface-variant">例如：请用一个生活中的例子解释本页的核心概念。</p>}
            {messages.map((message, index) => (
              <div key={`${message.role}-${index}`} className={`rounded-xl px-3 py-2 text-xs leading-5 ${message.role === 'user' ? 'ml-5 bg-secondary text-on-secondary' : 'mr-5 bg-surface-container-lowest text-on-surface'}`}>
                {message.content || (chatting && index === messages.length - 1 ? '正在思考…' : '暂无回复')}
              </div>
            ))}
          </div>
          <div className="mt-3 space-y-2">
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); handleQuestion() } }}
              placeholder={selectedBook ? '向当前教材提问…' : '先选择教材'}
              rows={3}
              className="w-full resize-none rounded-xl border border-outline-variant/60 bg-surface px-3 py-2 text-xs outline-none transition-colors focus:border-secondary"
              disabled={!selectedBook || chatting}
            />
            <button type="button" onClick={handleQuestion} disabled={!selectedBook || !question.trim() || chatting} className="flex w-full items-center justify-center gap-2 rounded-xl bg-secondary px-3 py-2.5 text-xs font-black text-on-secondary disabled:cursor-not-allowed disabled:opacity-50">
              {chatting ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              {chatting ? 'DeepTutor 正在回答' : '发送问题'}
            </button>
          </div>
        </aside>
      </div>

      <div className="rounded-2xl border border-outline-variant/60 bg-surface-container-lowest p-4 sm:p-5">
        <div className="mb-3 flex items-center gap-2">
          <Plus className="h-4 w-4 text-secondary" />
          <h3 className="text-sm font-black text-on-surface">现场准备：创建一本主题教材</h3>
        </div>
        <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_16rem_auto]">
          <input value={topic} onChange={(event) => setTopic(event.target.value)} placeholder="例如：Python 高阶函数与装饰器" className="rounded-xl border border-outline-variant/60 bg-surface px-3 py-2.5 text-xs outline-none focus:border-secondary" />
          <label className="flex items-center gap-2 rounded-xl border border-outline-variant/60 bg-surface px-3 py-2.5 text-xs text-on-surface-variant">
            <Database className="h-4 w-4 shrink-0 text-secondary" />
            <select value={selectedKnowledgeBase} onChange={(event) => setSelectedKnowledgeBase(event.target.value)} className="min-w-0 flex-1 bg-transparent outline-none">
              <option value="">不指定知识库</option>
              {knowledgeBases.map((base) => <option key={base.name} value={base.name}>{base.name}</option>)}
            </select>
          </label>
          <button type="button" onClick={() => { void handleCreateBook() }} disabled={!topic.trim() || creating || !token} className="inline-flex items-center justify-center gap-2 rounded-xl bg-secondary px-4 py-2.5 text-xs font-black text-on-secondary disabled:opacity-50">
            {creating ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            创建教材
          </button>
        </div>
      </div>
    </div>
  )
}
