import { useCallback, useMemo, useState } from "react";

import "./CapsuleLab.css";
import {
  buildCapsuleLookup,
  getCapsuleRiskBudgetAttackModes,
  getCapsuleRiskBudgetRowAttackModeId,
  getUniqueCapsuleOptions,
  pickCapsuleRiskBudgetRow,
  pickCapsuleRow,
  type CapsuleControlOption,
  type CapsuleLabArtifact,
  type CapsuleMonteCarloInterval,
  type CapsuleRiskBudgetArtifact,
  type CapsuleRiskBudgetContribution,
  type CapsuleRiskBudgetImprovement,
  type CapsuleRiskBudgetMetrics,
  type CapsuleRiskBudgetModeOption,
  type CapsuleRiskBudgetRow,
  type CapsuleSelectionPatch,
  type CapsuleSurvivalRow,
} from "./capsule_lab_contract";

interface CapsuleLabProps {
  artifact: CapsuleLabArtifact;
  artifactPath: string;
  riskBudgetArtifact?: CapsuleRiskBudgetArtifact;
  riskBudgetArtifactPath?: string;
}

interface ControlSelectProps {
  id: string;
  label: string;
  value: string;
  options: Array<Pick<CapsuleControlOption, "id" | "label"> & { detail?: string }>;
  detail?: string;
  onChange: (value: string) => void;
}

function formatProbability(value: number): string {
  if (!Number.isFinite(value)) {
    return "N/A";
  }
  return `${(value * 100).toFixed(1)}%`;
}

function formatMargin(value: number): string {
  if (!Number.isFinite(value)) {
    return "N/A";
  }
  return value.toFixed(2);
}

function formatOptionalProbability(value: number | undefined): string {
  return typeof value === "number" ? formatProbability(value) : "N/A";
}

function formatOptionalNumber(value: number | undefined): string {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(2) : "N/A";
}

function formatYears(value: number): string {
  if (!Number.isFinite(value)) {
    return "N/A";
  }
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(2)} Myr`;
  }
  return `${Math.round(value).toLocaleString()} yr`;
}

function stageStatusClass(status: CapsuleSurvivalRow["stages"][number]["status"]): string {
  return status.toLowerCase();
}

function ControlSelect(props: ControlSelectProps): JSX.Element {
  const { id, label, value, options, detail, onChange } = props;

  return (
    <div className="capsule-control-field">
      <label htmlFor={id}>{label}</label>
      <select id={id} value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => (
          <option key={option.id} value={option.id}>
            {option.label}
          </option>
        ))}
      </select>
      <p className="capsule-option-detail">{detail ?? "No committed row detail for this selection."}</p>
    </div>
  );
}

function sourceRefLabel(trustClass: string): string {
  return `trust ${trustClass}`;
}

function getRiskInterval(row: CapsuleRiskBudgetRow | undefined): CapsuleMonteCarloInterval | undefined {
  return row?.monte_carlo ?? row?.monteCarlo ?? row?.monte_carlo_interval ?? row?.monteCarloInterval;
}

function getRiskMetrics(row: CapsuleRiskBudgetRow | undefined): CapsuleRiskBudgetMetrics | undefined {
  return row?.risk_budget ?? row?.riskBudget;
}

function getUncertaintyDrivers(row: CapsuleRiskBudgetRow | undefined): CapsuleRiskBudgetContribution[] {
  return row?.top_uncertainty_drivers ?? row?.uncertainty_drivers ?? row?.uncertaintyDrivers ?? [];
}

function getFailureModeContributions(row: CapsuleRiskBudgetRow | undefined): CapsuleRiskBudgetContribution[] {
  return row?.failure_mode_contributions ?? row?.failureModeContributions ?? [];
}

function getRequiredImprovements(row: CapsuleRiskBudgetRow | undefined): CapsuleRiskBudgetImprovement[] {
  return row?.required_improvement ?? row?.required_improvements ?? row?.requiredImprovements ?? [];
}

function getQualificationRoadmap(row: CapsuleRiskBudgetRow | undefined): CapsuleRiskBudgetImprovement[] {
  return row?.qualification_roadmap ?? row?.qualificationRoadmap ?? [];
}

function contributionLabel(item: CapsuleRiskBudgetContribution): string {
  return item.label ?? item.name ?? item.mode ?? item.driver ?? "Unlabeled contribution";
}

function improvementLabel(item: CapsuleRiskBudgetImprovement): string {
  return item.label ?? item.name ?? (item.target_p50 ? `Reach p50 >= ${item.target_p50}` : "Unlabeled requirement");
}

function contributionDetail(item: CapsuleRiskBudgetContribution): string | undefined {
  return item.direction ?? item.note ?? item.source_ref;
}

function improvementDetail(item: CapsuleRiskBudgetImprovement): string | undefined {
  return item.rationale ?? item.evidence_needed;
}

function ContributionList(props: {
  title: string;
  items: CapsuleRiskBudgetContribution[];
  emptyLabel: string;
}): JSX.Element {
  const { title, items, emptyLabel } = props;

  return (
    <section className="capsule-risk-list" aria-label={title}>
      <h5>{title}</h5>
      {items.length > 0 ? (
        <ul>
          {items.map((item, index) => (
            <li key={`${contributionLabel(item)}-${index}`}>
              <div className="capsule-risk-list-row">
                <span>{contributionLabel(item)}</span>
                <span className="mono-cell">{formatOptionalProbability(item.contribution ?? item.share)}</span>
              </div>
              {contributionDetail(item) ? <p>{contributionDetail(item)}</p> : null}
            </li>
          ))}
        </ul>
      ) : (
        <p className="capsule-empty-note">{emptyLabel}</p>
      )}
    </section>
  );
}

function ImprovementList(props: {
  title: string;
  items: CapsuleRiskBudgetImprovement[];
  emptyLabel: string;
}): JSX.Element {
  const { title, items, emptyLabel } = props;

  return (
    <section className="capsule-risk-list" aria-label={title}>
      <h5>{title}</h5>
      {items.length > 0 ? (
        <ul>
          {items.map((item, index) => (
            <li key={`${improvementLabel(item)}-${index}`}>
              <div className="capsule-risk-list-row">
                <span>{improvementLabel(item)}</span>
                {item.status ? <span className="mono-cell">{item.status}</span> : null}
              </div>
              {item.threshold ? <code>{item.threshold}</code> : null}
              {improvementDetail(item) ? <p>{improvementDetail(item)}</p> : null}
            </li>
          ))}
        </ul>
      ) : (
        <p className="capsule-empty-note">{emptyLabel}</p>
      )}
    </section>
  );
}

function CapsuleRiskBudgetPanel(props: {
  artifact: CapsuleRiskBudgetArtifact | undefined;
  artifactPath: string | undefined;
  selectedRow: CapsuleSurvivalRow;
  selectedMode: CapsuleRiskBudgetModeOption | undefined;
  riskRow: CapsuleRiskBudgetRow | undefined;
}): JSX.Element {
  const { artifact, artifactPath, selectedRow, selectedMode, riskRow } = props;
  const pathLabel = artifactPath ?? "artifacts/capsule_risk_budget.v1.json";

  if (!artifact) {
    return (
      <section className="capsule-risk-panel pending" aria-label="Capsule risk budget artifact">
        <div className="capsule-risk-heading">
          <h4>Risk budget artifact pending</h4>
          <p>
            Expected artifact: <code>{pathLabel}</code>. Existing v1 survival rows remain visible until the v2
            budget is present in the browser dataset.
          </p>
        </div>
      </section>
    );
  }

  if (!riskRow) {
    return (
      <section className="capsule-risk-panel pending" aria-label="Capsule risk budget artifact">
        <div className="capsule-risk-heading">
          <h4>Risk budget</h4>
          <p>
            Source: <code>{pathLabel}</code>. No committed risk budget row is available for{" "}
            <code>{selectedRow.rowId}</code>.
          </p>
        </div>
      </section>
    );
  }

  const interval = getRiskInterval(riskRow);
  const metrics = getRiskMetrics(riskRow);
  const attackModeLabel = selectedMode?.label ?? getCapsuleRiskBudgetRowAttackModeId(riskRow);

  return (
    <section className="capsule-risk-panel" aria-label="Capsule risk budget artifact">
      <div className="capsule-risk-heading">
        <div>
          <h4>Risk budget</h4>
          <p>
            Source: <code>{pathLabel}</code>. Attack mode: <span>{attackModeLabel}</span>.
          </p>
        </div>
        {metrics?.status ? <span className="capsule-risk-status">{metrics.status}</span> : null}
      </div>

      <div className="capsule-risk-metrics" aria-label="Selected risk budget metrics">
        <div className="capsule-metric">
          <p className="capsule-metric-label">Monte Carlo interval</p>
          <p className="capsule-metric-value">
            {formatOptionalProbability(interval?.p05)} / {formatOptionalProbability(interval?.p50)} /{" "}
            {formatOptionalProbability(interval?.p95)}
          </p>
          <p className="capsule-metric-label">P05 / P50 / P95</p>
        </div>
        <div className="capsule-metric">
          <p className="capsule-metric-label">Budget survival</p>
          <p className="capsule-metric-value">{formatOptionalProbability(metrics?.survival_probability)}</p>
        </div>
        <div className="capsule-metric">
          <p className="capsule-metric-label">Loss probability</p>
          <p className="capsule-metric-value">{formatOptionalProbability(metrics?.loss_probability)}</p>
        </div>
        <div className="capsule-metric">
          <p className="capsule-metric-label">Budget margin</p>
          <p className="capsule-metric-value">{formatOptionalNumber(metrics?.margin)}</p>
        </div>
      </div>

      <div className="capsule-risk-detail-grid">
        <ContributionList
          title="Top uncertainty drivers"
          items={getUncertaintyDrivers(riskRow)}
          emptyLabel="No uncertainty drivers are committed for this row."
        />
        <ContributionList
          title="Failure mode contribution"
          items={getFailureModeContributions(riskRow)}
          emptyLabel="No failure-mode contribution rows are committed for this selection."
        />
        <ImprovementList
          title="Required improvements"
          items={getRequiredImprovements(riskRow)}
          emptyLabel="No improvement thresholds are committed for this row."
        />
        <ImprovementList
          title="Qualification roadmap"
          items={getQualificationRoadmap(riskRow)}
          emptyLabel="No qualification roadmap hints are committed for this row."
        />
      </div>
    </section>
  );
}

export function CapsuleLab({
  artifact,
  artifactPath,
  riskBudgetArtifact,
  riskBudgetArtifactPath,
}: CapsuleLabProps): JSX.Element {
  const lookup = useMemo(() => buildCapsuleLookup(artifact), [artifact]);
  const initialRowId = artifact.rows[0]?.rowId ?? "";
  const [selectedRowId, setSelectedRowId] = useState(initialRowId);
  const [selectedAttackModeId, setSelectedAttackModeId] = useState("");
  const [showJson, setShowJson] = useState(false);

  const selectedRow = lookup.rowsById.get(selectedRowId) ?? artifact.rows[0];
  const selectedTarget = selectedRow ? lookup.options.targetsById.get(selectedRow.targetId) : undefined;
  const selectedTime = selectedRow ? lookup.options.timeHorizonsById.get(selectedRow.timeId) : undefined;
  const selectedVelocity = selectedRow ? lookup.options.velocityBandsById.get(selectedRow.velocityId) : undefined;
  const selectedCapsule = selectedRow ? lookup.options.capsuleProfilesById.get(selectedRow.capsuleId) : undefined;

  const visibleOptions = useMemo(
    () => ({
      targets: getUniqueCapsuleOptions(artifact.controls.targets, artifact.rows, "targetId"),
      timeHorizons: getUniqueCapsuleOptions(artifact.controls.timeHorizons, artifact.rows, "timeId"),
      velocityBands: getUniqueCapsuleOptions(artifact.controls.velocityBands, artifact.rows, "velocityId"),
      capsuleProfiles: getUniqueCapsuleOptions(artifact.controls.capsuleProfiles, artifact.rows, "capsuleId"),
    }),
    [artifact],
  );
  const riskModeOptions = useMemo(
    () => getCapsuleRiskBudgetAttackModes(riskBudgetArtifact, selectedRow?.rowId),
    [riskBudgetArtifact, selectedRow?.rowId],
  );
  const selectedAttackMode =
    riskModeOptions.find((option) => option.id === selectedAttackModeId) ?? riskModeOptions[0];
  const selectedRiskBudgetRow = useMemo(
    () =>
      pickCapsuleRiskBudgetRow(riskBudgetArtifact, {
        capsuleRowId: selectedRow?.rowId,
        attackModeId: selectedAttackMode?.id,
      }),
    [riskBudgetArtifact, selectedAttackMode?.id, selectedRow?.rowId],
  );

  const selectedRowJson = useMemo(
    () =>
      JSON.stringify(
        selectedRow
          ? {
              ...selectedRow,
              risk_budget_row: selectedRiskBudgetRow,
              schema_version: artifact.schema_version,
            }
          : { schema_version: artifact.schema_version },
        null,
        2,
      ),
    [artifact.schema_version, selectedRiskBudgetRow, selectedRow],
  );

  const chooseRow = useCallback(
    (patch: CapsuleSelectionPatch) => {
      if (!selectedRow) {
        return;
      }
      const nextRow = pickCapsuleRow(artifact.rows, selectedRow, patch);
      setSelectedRowId(nextRow.rowId);
    },
    [artifact.rows, selectedRow],
  );

  if (!selectedRow) {
    return (
      <article className="capsule-lab">
        <h3>Capsule Survivability Lab</h3>
        <p>No capsule artifact rows are available.</p>
      </article>
    );
  }

  return (
    <article className="capsule-lab" aria-label="Capsule Survivability Lab">
      <header className="capsule-lab-header">
        <h3>Capsule Survivability Lab</h3>
        <p className="help-text">
          Artifact contract: <code>{artifactPath}</code>. The UI selects and formats committed rows.
        </p>
      </header>

      <div className="capsule-lab-grid">
        <aside className="capsule-control-panel" aria-label="Capsule artifact controls">
          <ControlSelect
            id="capsule-target"
            label="Target"
            value={selectedRow.targetId}
            options={visibleOptions.targets}
            detail={selectedTarget?.detail}
            onChange={(targetId) => chooseRow({ targetId })}
          />
          <ControlSelect
            id="capsule-time"
            label="Time"
            value={selectedRow.timeId}
            options={visibleOptions.timeHorizons}
            detail={selectedTime?.detail}
            onChange={(timeId) => chooseRow({ timeId })}
          />
          <ControlSelect
            id="capsule-velocity"
            label="Velocity"
            value={selectedRow.velocityId}
            options={visibleOptions.velocityBands}
            detail={selectedVelocity?.detail}
            onChange={(velocityId) => chooseRow({ velocityId })}
          />
          <ControlSelect
            id="capsule-profile"
            label="Capsule"
            value={selectedRow.capsuleId}
            options={visibleOptions.capsuleProfiles}
            detail={selectedCapsule?.detail}
            onChange={(capsuleId) => chooseRow({ capsuleId })}
          />
          {riskBudgetArtifact && riskModeOptions.length > 0 ? (
            <ControlSelect
              id="capsule-attack-mode"
              label="Attack mode"
              value={selectedAttackMode?.id ?? ""}
              options={riskModeOptions}
              detail={selectedAttackMode?.detail}
              onChange={setSelectedAttackModeId}
            />
          ) : null}

          <section aria-label="Capsule source references">
            <h4>Source refs</h4>
            <ul className="capsule-source-list">
              {artifact.source_index.slice(0, 8).map((source) => (
                <li key={source.source_id}>
                  <span>{source.label}</span> <code>{source.source_id}</code>{" "}
                  <span>({sourceRefLabel(source.trust_class)})</span>
                </li>
              ))}
            </ul>
          </section>
        </aside>

        <section className="capsule-output-panel" aria-label="Capsule survival outputs">
          <div className="capsule-output-topline">
            <div>
              <h4>Survival output</h4>
              <p className="capsule-verdict">{selectedRow.output.verdict}</p>
            </div>
            <span className={`capsule-band ${selectedRow.output.outcomeBand}`}>
              {selectedRow.output.outcomeBand}
            </span>
          </div>

          <div className="capsule-metrics-grid" aria-label="Selected artifact metrics">
            <div className="capsule-metric">
              <p className="capsule-metric-label">Survival probability</p>
              <p className="capsule-metric-value">{formatProbability(selectedRow.output.survivalProbability)}</p>
            </div>
            <div className="capsule-metric">
              <p className="capsule-metric-label">P05 / P95 survival</p>
              <p className="capsule-metric-value">
                {formatProbability(selectedRow.output.survivalP05)} / {formatProbability(selectedRow.output.survivalP95)}
              </p>
            </div>
            <div className="capsule-metric">
              <p className="capsule-metric-label">Data intact likelihood</p>
              <p className="capsule-metric-value">{formatProbability(selectedRow.output.dataIntegrityProbability)}</p>
            </div>
            <div className="capsule-metric">
              <p className="capsule-metric-label">Flight years</p>
              <p className="capsule-metric-value">{formatYears(selectedRow.flightYears)}</p>
            </div>
            <div className="capsule-metric">
              <p className="capsule-metric-label">Shield / thermal</p>
              <p className="capsule-metric-value">
                {formatMargin(selectedRow.output.shieldMargin)} / {formatMargin(selectedRow.output.thermalMargin)}
              </p>
            </div>
          </div>

          <div className="capsule-stage-grid" aria-label="Capsule stage checkpoints">
            {selectedRow.stages.map((stage) => (
              <section key={stage.stage} className="capsule-stage" aria-label={`${stage.stage} ${stage.label}`}>
                <div className="capsule-stage-header">
                  <p className="capsule-stage-title">
                    {stage.stage} | {stage.label}
                  </p>
                  <p className={`capsule-stage-status ${stageStatusClass(stage.status)}`}>{stage.status}</p>
                </div>
                <p className="capsule-stage-summary">{stage.summary}</p>
              </section>
            ))}
          </div>

          <div className="capsule-driver-row" aria-label="Dominant artifact drivers">
            {selectedRow.driverLabels.map((driver) => (
              <span className="capsule-driver" key={driver}>
                {driver}
              </span>
            ))}
          </div>

          <CapsuleRiskBudgetPanel
            artifact={riskBudgetArtifact}
            artifactPath={riskBudgetArtifactPath}
            selectedRow={selectedRow}
            selectedMode={selectedAttackMode}
            riskRow={selectedRiskBudgetRow}
          />

          <div className="capsule-artifact-footer">
            <p className="help-text mono-cell">
              row={selectedRow.rowId} | digest={selectedRow.artifactDigest} | v={selectedRow.velocityKmS.toFixed(2)} km/s
            </p>
            <button type="button" className="ghost-button" onClick={() => setShowJson((value) => !value)}>
              Open selected row JSON
            </button>
          </div>
          {showJson ? (
            <pre className="capsule-json-preview" aria-label="Selected row JSON">
              {selectedRowJson}
            </pre>
          ) : null}
        </section>
      </div>
    </article>
  );
}
