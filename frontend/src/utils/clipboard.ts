/**
 * Safely copy text to the clipboard across modern and legacy browser environments.
 * Returns true if the text was successfully written to the clipboard, false otherwise.
 */
export async function copyTextToClipboard(text: string): Promise<boolean> {
  if (!text || typeof text !== 'string') {
    return false
  }

  // 1. Try modern navigator.clipboard API if available
  if (
    typeof navigator !== 'undefined' &&
    navigator.clipboard &&
    typeof navigator.clipboard.writeText === 'function'
  ) {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch {
      // Fall through to legacy fallback on failure (e.g. permission denied or unsupported)
    }
  }

  // 2. Legacy fallback using document.execCommand for older browsers or non-secure contexts
  if (typeof document !== 'undefined' && typeof document.execCommand === 'function') {
    try {
      const textArea = document.createElement('textarea')
      textArea.value = text
      textArea.setAttribute('readonly', '')
      textArea.style.position = 'fixed'
      textArea.style.opacity = '0'
      textArea.style.pointerEvents = 'none'
      document.body.appendChild(textArea)
      textArea.focus()
      textArea.select()
      const successful = document.execCommand('copy')
      document.body.removeChild(textArea)
      return Boolean(successful)
    } catch {
      return false
    }
  }

  return false
}
