import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

export interface DeepTutorSavedQuestion {
  id: string
  bookId: string
  pageId: string
  question: string
  createdAt: string
}

export interface DeepTutorStudyState {
  completedPages: Record<string, string[]>
  notes: Record<string, string>
  savedQuestions: DeepTutorSavedQuestion[]
  lastOpened: { bookId: string; pageId: string } | null
}

const EMPTY_STATE: DeepTutorStudyState = {
  completedPages: {},
  notes: {},
  savedQuestions: [],
  lastOpened: null,
}

function storageKey(token: string | null): string {
  return `campus-agent:deeptutor-study:${token?.slice(-12) || 'guest'}`
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
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
    const lastOpened = isRecord(parsed.lastOpened)
      && typeof parsed.lastOpened.bookId === 'string'
      && typeof parsed.lastOpened.pageId === 'string'
      ? { bookId: parsed.lastOpened.bookId, pageId: parsed.lastOpened.pageId }
      : null
    return { completedPages, notes, savedQuestions, lastOpened }
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

  const setPageNote = useCallback((bookId: string, pageId: string, note: string) => {
    const key = `${bookId}:${pageId}`
    update((current) => ({ ...current, notes: { ...current.notes, [key]: note } }))
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
    setLastOpened,
    notesCount,
  }
}
