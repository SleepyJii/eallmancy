// components/CodeViewer.tsx
import React, { useMemo, useState } from 'react';
import { useGlobalStore } from '../../state/globalStore';



type Props = {
  lines?: string[];
  highlightSpec?: (number | string)[];
  showLineNumbers?: boolean;
  maxHeight?: number;
  fontSize?: number;
  onLineClick?: (line: number, text: string) => void;
  lineColors?: Map<number, string>;            // (optional) background per line (single color)
  lineGutterColors?: Map<number, string[]>;    // NEW: multiple colors per line
  gutterPosition?: 'left' | 'right';           // NEW
  gutterWidth?: number;                        // px, NEW
};

function useHighlightSet(spec?: (number | string)[]) {
  return useMemo(() => {
    const set = new Set<number>();
    if (!spec) return set;
    for (const item of spec) {
      if (typeof item === 'number' && Number.isFinite(item)) set.add(item);
      else if (typeof item === 'string') {
        const [a, b] = item.split('-').map((n) => parseInt(n, 10));
        if (Number.isFinite(a) && Number.isFinite(b)) {
          for (let i = Math.min(a, b); i <= Math.max(a, b); i++) set.add(i);
        }
      }
    }
    return set;
  }, [spec]);
}

export default function CodeViewer({
  lines,
  highlightSpec,
  showLineNumbers = true,
  maxHeight = 420,
  fontSize = 13,
  onLineClick,
  lineColors,
  lineGutterColors,
  gutterPosition = 'left',
  gutterWidth = 10,
}: Props) {
  const data = lines ?? [];
  const highlights = useHighlightSet(highlightSpec);

  const [copied, setCopied] = useState(false);
  const allText = useMemo(() => data.join('\n'), [data]);

  const copyAll = async () => {
    try {
      await navigator.clipboard.writeText(allText);
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    } catch {}
  };

  const hasGutter = !!lineGutterColors;

  // Build grid template based on gutter & line numbers
  const gridCols = useMemo(() => {
    const cols: string[] = [];
    if (hasGutter && gutterPosition === 'left') cols.push(`${gutterWidth}px`);
    if (showLineNumbers) cols.push('auto');
    cols.push('1fr');
    if (hasGutter && gutterPosition === 'right') cols.push(`${gutterWidth}px`);
    return cols.join(' ');
  }, [hasGutter, gutterPosition, gutterWidth, showLineNumbers]);

  return (
    <div style={{ border: '1px solid #ccc', borderRadius: 8, overflow: 'hidden', background: '#1e1e1e' }}>
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '6px 10px',
          background: '#2b2b2b',
          color: '#ddd',
          fontSize: '0.9em',
        }}
      >
        <div>Code</div>
        <button
          onClick={copyAll}
          style={{
            border: 'none',
            background: copied ? '#3a7d44' : '#444',
            color: '#fff',
            padding: '4px 8px',
            borderRadius: 6,
            cursor: 'pointer',
          }}
        >
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>

      {/* Body */}
      <div
        style={{
          maxHeight,
          overflow: 'auto',
          fontFamily:
            'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
          fontSize,
          lineHeight: 1.5,
          tabSize: 2,
          padding: '8px 0',
          color: '#e6e6e6',
        }}
      >
        {data.length === 0 ? (
          <div style={{ padding: 10, color: '#aaa' }}>No code to display.</div>
        ) : (
          data.map((text, idx) => {
            const lineNo = idx ;//+ 1;
            const isHL = highlights.has(lineNo);
            const bg = lineColors?.get(lineNo) ?? (isHL ? '#343a40' : 'transparent');
            const gutterColors = lineGutterColors?.get(lineNo) ?? [];

            // Gutter stripes: side-by-side narrow bars filling the gutter
            const Gutter = hasGutter ? (
              <div
                aria-hidden
                style={{
                  width: gutterWidth,
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'row',
                }}
              >
                {gutterColors.length === 0 ? (
                  <div style={{ flex: 1, opacity: 0 }} />
                ) : (
                  gutterColors.map((c, i) => (
                    <div
                      key={i}
                      style={{
                        flex: 1,
                        background: c,
                        borderLeft: i === 0 ? 'none' : '1px solid rgba(0,0,0,0.15)',
                      }}
                    />
                  ))
                )}
              </div>
            ) : null;

            return (
              <div
                key={idx}
                onClick={onLineClick ? () => onLineClick(lineNo, text) : undefined}
                style={{
                  display: 'grid',
                  gridTemplateColumns: gridCols,
                  gap: '12px',
                  padding: '0 12px',
                  background: bg,
                  alignItems: 'stretch',
                }}
              >
                {hasGutter && gutterPosition === 'left' && Gutter}

                {showLineNumbers && (
                  <div style={{ textAlign: 'right', color: '#8b949e', userSelect: 'none', width: 36 }}>
                    {lineNo}
                  </div>
                )}

                <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                  <code>{text}</code>
                </pre>

                {hasGutter && gutterPosition === 'right' && Gutter}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}







// type Props = {
//   lines?: string[];                         // optional; falls back to store
//   highlightSpec?: (number | string)[];      // e.g. [1, '3-5']
//   showLineNumbers?: boolean;
//   maxHeight?: number;
//   fontSize?: number;
//   onLineClick?: (line: number, text: string) => void;
//   lineColors?: Map<number, string>;         // NEW: per-line background colors
// };

// function useHighlightSet(spec?: (number | string)[]) {
//   return useMemo(() => {
//     const set = new Set<number>();
//     if (!spec) return set;
//     for (const item of spec) {
//       if (typeof item === 'number' && Number.isFinite(item)) {
//         set.add(item);
//       } else if (typeof item === 'string') {
//         const [a, b] = item.split('-').map((n) => parseInt(n, 10));
//         if (Number.isFinite(a) && Number.isFinite(b)) {
//           const start = Math.min(a, b);
//           const end = Math.max(a, b);
//           for (let i = start; i <= end; i++) set.add(i);
//         }
//       }
//     }
//     return set;
//   }, [spec]);
// }

// export default function CodeViewer({
//   lines,
//   highlightSpec,
//   showLineNumbers = true,
//   maxHeight = 420,
//   fontSize = 13,
//   onLineClick,
//   lineColors,
// }: Props) {
//   // Fallback to store lines if prop not provided
//   // const storeLines = useGlobalStore((s) => s.global.code?.lines || []);
//   const data = lines ?? [] ;

//   const highlights = useHighlightSet(highlightSpec);    // ✅ defined now
//   console.log('built highlightspec');

//   const [copied, setCopied] = useState(false);
//   const allText = useMemo(() => data.join('\n'), [data]);

//   const copyAll = async () => {
//     try {
//       await navigator.clipboard.writeText(allText);
//       setCopied(true);
//       setTimeout(() => setCopied(false), 1200);
//     } catch {}
//   };
//   console.log('about to render codeview');

//   return (
//     <div style={{ border: '1px solid #ccc', borderRadius: 8, overflow: 'hidden', background: '#1e1e1e' }}>
//       {/* Header */}
//       <div
//         style={{
//           display: 'flex',
//           alignItems: 'center',
//           justifyContent: 'space-between',
//           padding: '6px 10px',
//           background: '#2b2b2b',
//           color: '#ddd',
//           fontSize: '0.9em',
//         }}
//       >
//         <div>Code</div>
//         <button
//           onClick={copyAll}
//           style={{
//             border: 'none',
//             background: copied ? '#3a7d44' : '#444',
//             color: '#fff',
//             padding: '4px 8px',
//             borderRadius: 6,
//             cursor: 'pointer',
//           }}
//         >
//           {copied ? 'Copied!' : 'Copy'}
//         </button>
//       </div>

//       {/* Body */}
//       <div
//         style={{
//           maxHeight,
//           overflow: 'auto',
//           fontFamily:
//             'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
//           fontSize,
//           lineHeight: 1.5,
//           tabSize: 2,
//           padding: '8px 0',
//           color: '#e6e6e6',
//         }}
//       >
//         {data.length === 0 ? (
//           <div style={{ padding: 10, color: '#aaa' }}>No code to display.</div>
//         ) : (
//           data.map((text, idx) => {
//             const lineNo = idx + 1;
//             const isHL = highlights.has(lineNo);
//             const bg = lineColors?.get(lineNo) ?? (isHL ? '#343a40' : 'transparent');
//             return (
//               <div
//                 key={idx}
//                 onClick={onLineClick ? () => onLineClick(lineNo, text) : undefined}
//                 style={{
//                   display: 'grid',
//                   gridTemplateColumns: showLineNumbers ? 'auto 1fr' : '1fr',
//                   gap: '12px',
//                   padding: '0 12px',
//                   background: bg,
//                 }}
//               >
//                 {showLineNumbers && (
//                   <div style={{ textAlign: 'right', color: '#8b949e', userSelect: 'none', width: 36 }}>
//                     {lineNo}
//                   </div>
//                 )}
//                 <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
//                   <code>{text}</code>
//                 </pre>
//               </div>
//             );
//           })
//         )}
//       </div>
//     </div>
//   );
// }
