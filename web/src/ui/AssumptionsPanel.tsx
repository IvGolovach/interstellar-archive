const ASSUMPTIONS: readonly string[] = [
  "Simplified encounter geometry and proxy-style mission model assumptions.",
  "Not a full GR trajectory integrator; Schwarzschild baseline is defined in the mission layer.",
  "Environment acceptance filter is proxy-based in v1.",
  "Realistic and speculative knobs coexist; speculative settings break realism boundaries.",
  "Survival and integrity terms are parametric envelopes, not hardware qualification evidence.",
];

const LIMITATIONS_URL =
  "https://github.com/IvGolovach/interstellar-archive/blob/main/LIMITATIONS.md";

export function AssumptionsPanel(): JSX.Element {
  return (
    <section className="panel assumptions-panel" aria-label="Model assumptions">
      <h2>Assumptions</h2>
      <ul className="assumptions-list">
        {ASSUMPTIONS.map((assumption) => (
          <li key={assumption}>{assumption}</li>
        ))}
      </ul>
      <p className="help-text">
        See detailed caveats in{" "}
        <a href={LIMITATIONS_URL} target="_blank" rel="noreferrer">
          LIMITATIONS.md
        </a>
        .
      </p>
    </section>
  );
}
