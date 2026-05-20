import { CompactValue } from "./CompactValue";

interface ResultReproducibilitySectionProps {
  checksumValue: string | null;
  engineVersion: string;
  schemaVersion: string;
  lastVerifiedCommitSha: string;
}

export function ResultReproducibilitySection(
  props: ResultReproducibilitySectionProps,
): JSX.Element {
  const {
    checksumValue,
    engineVersion,
    schemaVersion,
    lastVerifiedCommitSha,
  } = props;

  return (
    <div className="integrity-block">
      <h3>Reproducibility</h3>
      <div className="repro-grid">
        <div className="artifact-value">
          <span className="artifact-label">Engine version</span>
          <code className="inline-code-pill">{engineVersion}</code>
        </div>
        <div className="artifact-value">
          <span className="artifact-label">Schema version</span>
          <code className="inline-code-pill">{schemaVersion}</code>
        </div>
        <div className="artifact-value">
          <span className="artifact-label">Golden checksum</span>
          <CompactValue value={checksumValue} placeholder="run scenario first" />
        </div>
        <div className="artifact-value">
          <span className="artifact-label">Last verified commit</span>
          <CompactValue value={lastVerifiedCommitSha} placeholder="unknown" />
        </div>
      </div>
    </div>
  );
}
