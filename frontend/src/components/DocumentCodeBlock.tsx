import { useEffect, useRef, useState } from 'react'
import { Check, Copy } from 'lucide-react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism'

interface DocumentCodeBlockProps {
  code: string
  language?: string
  className?: string
}

export default function DocumentCodeBlock({
  code,
  language,
  className,
}: DocumentCodeBlockProps) {
  const [copied, setCopied] = useState(false)
  const copiedTimeoutRef = useRef<number | null>(null)

  useEffect(() => {
    return () => {
      if (copiedTimeoutRef.current !== null) {
        window.clearTimeout(copiedTimeoutRef.current)
      }
    }
  }, [])

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
      if (copiedTimeoutRef.current !== null) {
        window.clearTimeout(copiedTimeoutRef.current)
      }
      copiedTimeoutRef.current = window.setTimeout(() => setCopied(false), 2000)
    } catch {
      setCopied(false)
    }
  }

  return (
    <div className="document-code-block not-prose relative my-4 overflow-hidden rounded-xl border">
      <button
        type="button"
        onClick={handleCopy}
        className="document-code-copy-button absolute right-3 top-3 inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium"
        aria-label="Copy code block"
      >
        {copied ? (
          <>
            <Check className="h-3.5 w-3.5" />
            Copied!
          </>
        ) : (
          <>
            <Copy className="h-3.5 w-3.5" />
            Copy
          </>
        )}
      </button>
      <SyntaxHighlighter
        language={language === 'text' ? undefined : language}
        style={oneLight}
        wrapLongLines
        customStyle={{
          background: 'transparent',
          borderRadius: 0,
          fontSize: '0.875rem',
          margin: 0,
          padding: '1rem',
          paddingTop: '3rem',
        }}
        codeTagProps={className ? { className } : undefined}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  )
}
