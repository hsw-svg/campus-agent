import ReactMarkdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface MarkdownProps {
  content: string
  className?: string
}

const components: Components = {
  h1: ({ node: _node, ...props }) => <h1 className="mt-3 mb-2 text-base font-black text-on-surface" {...props} />,
  h2: ({ node: _node, ...props }) => <h2 className="mt-3 mb-1.5 text-sm font-extrabold text-on-surface" {...props} />,
  h3: ({ node: _node, ...props }) => <h3 className="mt-2.5 mb-1 text-xs font-extrabold text-on-surface" {...props} />,
  h4: ({ node: _node, ...props }) => <h4 className="mt-2 mb-1 text-[11px] font-bold text-on-surface" {...props} />,
  p: ({ node: _node, ...props }) => <p className="my-1.5 text-sm leading-relaxed text-on-surface" {...props} />,
  ul: ({ node: _node, ...props }) => <ul className="my-1.5 list-disc space-y-1 pl-5 text-sm leading-relaxed text-on-surface" {...props} />,
  ol: ({ node: _node, ...props }) => <ol className="my-1.5 list-decimal space-y-1 pl-5 text-sm leading-relaxed text-on-surface" {...props} />,
  li: ({ node: _node, ...props }) => <li className="marker:text-outline" {...props} />,
  a: ({ node: _node, ...props }) => <a className="text-primary underline underline-offset-2 hover:opacity-80" target="_blank" rel="noreferrer" {...props} />,
  strong: ({ node: _node, ...props }) => <strong className="font-extrabold text-on-surface" {...props} />,
  em: ({ node: _node, ...props }) => <em className="italic" {...props} />,
  blockquote: ({ node: _node, ...props }) => <blockquote className="my-2 border-l-2 border-primary/40 bg-primary/5 px-3 py-1.5 text-sm italic text-on-surface" {...props} />,
  hr: () => <hr className="my-3 border-outline-variant/60" />,
  table: ({ node: _node, ...props }) => (
    <div className="my-2 overflow-x-auto">
      <table className="min-w-full border-collapse text-xs" {...props} />
    </div>
  ),
  thead: ({ node: _node, ...props }) => <thead className="bg-surface-container" {...props} />,
  th: ({ node: _node, ...props }) => <th className="border border-outline-variant px-2 py-1 text-left font-bold text-on-surface" {...props} />,
  td: ({ node: _node, ...props }) => <td className="border border-outline-variant px-2 py-1 align-top text-on-surface" {...props} />,
  code: ({ node: _node, className, children, ...props }) => {
    const inline = !className
    if (inline) {
      return <code className="rounded bg-surface-container px-1 py-0.5 text-[12px] font-mono text-on-surface" {...props}>{children}</code>
    }
    return <code className={`${className ?? ''} block`} {...props}>{children}</code>
  },
  pre: ({ node: _node, ...props }) => (
    <pre className="my-2 overflow-x-auto rounded-lg bg-surface-container p-3 text-[12px] leading-relaxed text-on-surface" {...props} />
  ),
}

export default function Markdown({ content, className }: MarkdownProps) {
  return (
    <div className={className}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>{content}</ReactMarkdown>
    </div>
  )
}
