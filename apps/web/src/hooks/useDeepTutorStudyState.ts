import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

export interface DeepTutorSavedQuestion {
  id: string
  bookId: string
  pageId: string
  question: string
  createdAt: string
}

export interface DeepTutorChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
}

export interface DeepTutorNoteMeta {
  bookTitle?: string
  pageTitle?: string
  updatedAt: string
}

export interface DeepTutorStudyState {
  completedPages: Record<string, string[]>
  notes: Record<string, string>
  noteMeta: Record<string, DeepTutorNoteMeta>
  savedQuestions: DeepTutorSavedQuestion[]
  chatHistory: Record<string, DeepTutorChatMessage[]>
  chatSessions: Record<string, string>
  lastOpened: { bookId: string; pageId: string } | null
}

const EMPTY_STATE: DeepTutorStudyState = {
  completedPages: {},
  notes: {},
  noteMeta: {},
  savedQuestions: [],
  chatHistory: {},
  chatSessions: {},
  lastOpened: null,
}

const MAX_CHAT_MESSAGES = 60
const MAX_CHAT_MESSAGE_LENGTH = 12_000

function storageKey(token: string | null): string {
  return `campus-agent:deeptutor-study:${token?.slice(-12) || 'guest'}`
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function chatMessagesFromUnknown(value: unknown): DeepTutorChatMessage[] {
  if (!Array.isArray(value)) return []
  return value.flatMap((item, index) => {
    if (!isRecord(item) || (item.role !== 'user' && item.role !== 'assistant') || typeof item.content !== 'string') return []
    return [{
      id: typeof item.id === 'string' ? item.id : `restored-${index}`,
      role: item.role as DeepTutorChatMessage['role'],
      content: item.content.slice(0, MAX_CHAT_MESSAGE_LENGTH),
    }]
  }).slice(-MAX_CHAT_MESSAGES)
}

function readState(token: string | null): DeepTutorStudyState {
  if (typeof window === 'undefined') return EMPTY_STATE
  try {
    const parsed: unknown = JSON.parse(window.localStorage.getItem(storageKey(token)) || 'null')
    if (!isRecord(parsed)) return EMPTY_STATE
    const completedPages = isRecord(parsed.completedPages)
      ? Object.fromEntries(Object.entries(parsed.completedPages).flatMap(([bookId, pages]) => (
        Array.isArray(pages) ? [[bookId, pages.filter((pageId): pageId is string => typeof pageId === 'string')]] : []
      )))
      : {}
    const notes = isRecord(parsed.notes)
      ? Object.fromEntries(Object.entries(parsed.notes).flatMap(([key, note]) => (
        typeof note === 'string' ? [[key, note]] : []
      )))
      : {}
    const noteMeta = isRecord(parsed.noteMeta)
      ? Object.fromEntries(Object.entries(parsed.noteMeta).flatMap(([key, meta]) => {
        if (!isRecord(meta) || typeof meta.updatedAt !== 'string') return []
        return [[key, {
          ...(typeof meta.bookTitle === 'string' ? { bookTitle: meta.bookTitle } : {}),
          ...(typeof meta.pageTitle === 'string' ? { pageTitle: meta.pageTitle } : {}),
          updatedAt: meta.updatedAt,
        }]]
      }))
      : {}
    const savedQuestions = Array.isArray(parsed.savedQuestions)
      ? parsed.savedQuestions.filter((item): item is DeepTutorSavedQuestion => (
        isRecord(item)
        && typeof item.id === 'string'
        && typeof item.bookId === 'string'
        && typeof item.pageId === 'string'
        && typeof item.question === 'string'
        && typeof item.createdAt === 'string'
      ))
      : []
    const chatHistory = isRecord(parsed.chatHistory)
      ? Object.fromEntries(Object.entries(parsed.chatHistory).flatMap(([key, messages]) => {
        const normalized = chatMessagesFromUnknown(messages)
        return normalized.length > 0 ? [[key, normalized]] : []
      }))
      : {}
    const chatSessions = isRecord(parsed.chatSessions)
      ? Object.fromEntries(Object.entries(parsed.chatSessions).flatMap(([key, sessionId]) => (
        typeof sessionId === 'string' && sessionId.trim() ? [[key, sessionId]] : []
      )))
      : {}
    const lastOpened = isRecord(parsed.lastOpened)
      && typeof parsed.lastOpened.bookId === 'string'
      && typeof parsed.lastOpened.pageId === 'string'
      ? { bookId: parsed.lastOpened.bookId, pageId: parsed.lastOpened.pageId }
      : null
    return { completedPages, notes, noteMeta, savedQuestions, chatHistory, chatSessions, lastOpened }
  } catch {
    return EMPTY_STATE
  }
}

export default function useDeepTutorStudyState(token: string | null) {
  const [state, setState] = useState<DeepTutorStudyState>(() => readState(token))
  const skipPersistRef = useRef(false)

  useEffect(() => {
    skipPersistRef.current = true
    setState(readState(token))
  }, [token])

  useEffect(() => {
    if (typeof window === 'undefined') return
    if (skipPersistRef.current) {
      skipPersistRef.current = false
      return
    }
    window.localStorage.setItem(storageKey(token), JSON.stringify(state))
  }, [state, token])

  const update = useCallback((updater: (current: DeepTutorStudyState) => DeepTutorStudyState) => {
    setState((current) => updater(current))
  }, [])

  const completedForBook = useCallback((bookId: string): string[] => state.completedPages[bookId] ?? [], [state.completedPages])

  const isPageCompleted = useCallback((bookId: string, pageId: string): boolean => (
    completedForBook(bookId).includes(pageId)
  ), [completedForBook])

  const markPageCompleted = useCallback((bookId: string, pageId: string) => {
    update((current) => {
      const pages = current.completedPages[bookId] ?? []
      if (pages.includes(pageId)) return current
      return { ...current, completedPages: { ...current.completedPages, [bookId]: [...pages, pageId] } }
    })
  }, [update])

  const setPageNote = useCallback((
    bookId: string,
    pageId: string,
    note: string,
    meta?: Omit<DeepTutorNoteMeta, 'updatedAt'>,
  ) => {
    const key = `${bookId}:${pageId}`
    update((current) => {
      const notes = { ...current.notes }
      const noteMeta = { ...current.noteMeta }
      if (!note.trim()) {
        delete notes[key]
        delete noteMeta[key]
      } else {
        notes[key] = note
        noteMeta[key] = {
          ...(meta?.bookTitle ? { bookTitle: meta.bookTitle } : {}),
          ...(meta?.pageTitle ? { pageTitle: meta.pageTitle } : {}),
          updatedAt: new Date().toISOString(),
        }
      }
      return { ...current, notes, noteMeta }
    })
  }, [update])

  const saveQuestion = useCallback((bookId: string, pageId: string, question: string) => {
    const trimmed = question.trim()
    if (!trimmed) return
    update((current) => {
      if (current.savedQuestions.some((item) => item.bookId === bookId && item.pageId === pageId && item.question === trimmed)) {
        return current
      }
      return {
        ...current,
        savedQuestions: [
          ...current.savedQuestions,
          { id: `${Date.now()}-${Math.random().toString(36).slice(2)}`, bookId, pageId, question: trimmed, createdAt: new Date().toISOString() },
        ].slice(-50),
      }
    })
  }, [update])

  const chatHistoryForPage = useCallback((bookId: string, pageId: string): DeepTutorChatMessage[] => (
    state.chatHistory[`${bookId}:${pageId}`] ?? []
  ), [state.chatHistory])

  const setChatHistory = useCallback((bookId: string, pageId: string, messages: DeepTutorChatMessage[]) => {
    const key = `${bookId}:${pageId}`
    const normalized = messages.map((message) => ({
      ...message,
      content: message.content.slice(0, MAX_CHAT_MESSAGE_LENGTH),
    })).slice(-MAX_CHAT_MESSAGES)
    update((current) => ({
      ...current,
      chatHistory: normalized.length > 0
        ? { ...current.chatHistory, [key]: normalized }
        : Object.fromEntries(Object.entries(current.chatHistory).filter(([entryKey]) => entryKey !== key)),
    }))
  }, [update])

  const clearChatHistory = useCallback((bookId: string, pageId: string) => {
    const key = `${bookId}:${pageId}`
    update((current) => ({
      ...current,
      chatHistory: Object.fromEntries(Object.entries(current.chatHistory).filter(([entryKey]) => entryKey !== key)),
      chatSessions: Object.fromEntries(Object.entries(current.chatSessions).filter(([entryKey]) => entryKey !== key)),
    }))
  }, [update])

  const chatSessionForPage = useCallback((bookId: string, pageId: string): string | null => (
    state.chatSessions[`${bookId}:${pageId}`] ?? null
  ), [state.chatSessions])

  const setChatSession = useCallback((bookId: string, pageId: string, sessionId: string | null) => {
    const key = `${bookId}:${pageId}`
    update((current) => {
      const chatSessions = { ...current.chatSessions }
      if (sessionId?.trim()) chatSessions[key] = sessionId
      else delete chatSessions[key]
      return { ...current, chatSessions }
    })
  }, [update])

  const setLastOpened = useCallback((bookId: string, pageId: string) => {
    update((current) => ({ ...current, lastOpened: { bookId, pageId } }))
  }, [update])

  const notesCount = useMemo(() => Object.values(state.notes).filter((note) => note.trim()).length, [state.notes])

  return {
    state,
    completedForBook,
    isPageCompleted,
    markPageCompleted,
    setPageNote,
    saveQuestion,
    chatHistoryForPage,
    setChatHistory,
    clearChatHistory,
    chatSessionForPage,
    setChatSession,
    setLastOpened,
    notesCount,
  }
}
