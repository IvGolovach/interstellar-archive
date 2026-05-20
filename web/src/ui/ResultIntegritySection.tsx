import { CompactValue } from "./CompactValue";

interface ResultIntegritySectionProps {
  checksumValue: string | null;
}

export function ResultIntegritySection(
  props: ResultIntegritySectionProps,
): JSX.Element {
  const { checksumValue } = props;

  return (
    <div className="integrity-block">
      <h3>Integrity</h3>
      <div className="artifact-value">
        <span className="artifact-label">Golden checksum</span>
        <CompactValue value={checksumValue} placeholder="run scenario first" />
      </div>
    </div>
  );
}
