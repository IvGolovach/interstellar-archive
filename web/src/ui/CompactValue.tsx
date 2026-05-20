import { useEffect, useMemo, useState } from "react";

interface CompactValueProps {
  value: string | null;
  placeholder: string;
}

function shortenValue(value: string): string {
  if (value.length <= 18) {
    return value;
  }
  return `${value.slice(0, 8)}...${value.slice(-6)}`;
}

async function copyText(value: string): Promise<void> {
  if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value);
    return;
  }

  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.style.position = "fixed";
  textarea.style.top = "0";
  textarea.style.left = "0";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  document.execCommand("copy");
  document.body.removeChild(textarea);
}

export function CompactValue(props: CompactValueProps): JSX.Element {
  const { value, placeholder } = props;
  const [expanded, setExpanded] = useState(false);
  const [copyState, setCopyState] = useState<"idle" | "done" | "error">("idle");

  useEffect(() => {
    setExpanded(false);
    setCopyState("idle");
  }, [value]);

  useEffect(() => {
    if (copyState === "idle") {
      return;
    }
    const timeoutId = window.setTimeout(() => setCopyState("idle"), 1400);
    return () => window.clearTimeout(timeoutId);
  }, [copyState]);

  const display = useMemo(() => {
    if (!value) {
      return placeholder;
    }
    return expanded ? value : shortenValue(value);
  }, [expanded, placeholder, value]);

  return (
    <div className="compact-value">
      <code className="compact-value-text" title={value ?? placeholder}>
        {display}
      </code>
      <div className="compact-actions">
        <button
          className="ghost-button"
          type="button"
          disabled={!value}
          onClick={async () => {
            if (!value) {
              return;
            }
            try {
              await copyText(value);
              setCopyState("done");
            } catch {
              setCopyState("error");
            }
          }}
        >
          {copyState === "done" ? "Copied" : copyState === "error" ? "Copy failed" : "Copy"}
        </button>
        {value && value.length > 18 ? (
          <button className="ghost-button" type="button" onClick={() => setExpanded((current) => !current)}>
            {expanded ? "Collapse" : "Expand"}
          </button>
        ) : null}
      </div>
    </div>
  );
}
