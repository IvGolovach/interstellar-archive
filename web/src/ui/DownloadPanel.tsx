import type { SimInput, SimOutput } from "../../../sim/public/types";
import { CompactValue } from "./CompactValue";

interface DownloadPanelProps {
  input: SimInput | null;
  output: SimOutput | null;
  checksum: string | null;
}

function downloadText(filename: string, content: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

const REPRO_SNIPPET = "npm run golden:check --prefix web";

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

export function DownloadPanel(props: DownloadPanelProps): JSX.Element {
  const { input, output, checksum } = props;
  const canDownload = input !== null && output !== null;

  return (
    <section className="artifacts-panel">
      <h2>Artifacts</h2>
      <p className="help-text">
        Download exact input/output JSON for audit or local replay. Checksum is SHA-256 over canonical output payload.
      </p>
      <div className="download-row">
        <button
          type="button"
          disabled={!canDownload}
          onClick={() => {
            if (!input) {
              return;
            }
            downloadText("sim_input.json", JSON.stringify(input, null, 2), "application/json");
          }}
        >
          Download SimInput
        </button>
        <button
          type="button"
          disabled={!canDownload}
          onClick={() => {
            if (!output) {
              return;
            }
            downloadText("sim_output.json", JSON.stringify(output, null, 2), "application/json");
          }}
        >
          Download SimOutput
        </button>
        <button
          className="ghost-button"
          type="button"
          disabled={!checksum}
          onClick={async () => {
            if (!checksum) {
              return;
            }
            await copyText(checksum);
          }}
        >
          Copy checksum
        </button>
      </div>
      <div className="artifact-value">
        <span className="artifact-label">Checksum</span>
        <CompactValue value={checksum} placeholder="run scenario first" />
      </div>
      <div className="artifact-value">
        <span className="artifact-label">Reproduce locally</span>
        <div className="snippet-row">
          <code className="snippet">{REPRO_SNIPPET}</code>
          <button
            className="ghost-button"
            type="button"
            onClick={async () => {
              await copyText(REPRO_SNIPPET);
            }}
          >
            Copy command
          </button>
        </div>
      </div>
    </section>
  );
}
