import type {
  CapsuleControlOption,
  CapsuleSurvivabilityLabArtifact,
  CapsuleSurvivalRow,
} from "../../lib/parameter_drilldown_dataset_contract";

export type { CapsuleControlOption, CapsuleSurvivabilityLabArtifact as CapsuleLabArtifact, CapsuleSurvivalRow };

export interface CapsuleSelection {
  targetId: string;
  timeId: string;
  velocityId: string;
  capsuleId: string;
}

export interface CapsuleLookup {
  rowsById: Map<string, CapsuleSurvivalRow>;
  options: {
    targetsById: Map<string, CapsuleControlOption>;
    timeHorizonsById: Map<string, CapsuleControlOption>;
    velocityBandsById: Map<string, CapsuleControlOption>;
    capsuleProfilesById: Map<string, CapsuleControlOption>;
  };
}

export type CapsuleSelectionPatch = Partial<CapsuleSelection>;

export interface CapsuleRiskBudgetAttackMode {
  id?: string;
  attack_mode_id?: string;
  mode_id?: string;
  label?: string;
  description?: string;
  detail?: string;
}

export interface CapsuleRiskBudgetAttackModeSet {
  default_row_id?: string;
  modes?: CapsuleRiskBudgetAttackMode[];
}

export interface CapsuleRiskBudgetModeOption {
  id: string;
  label: string;
  detail?: string;
}

export interface CapsuleMonteCarloInterval {
  p05?: number;
  p50?: number;
  p95?: number;
  confidence_level?: number;
}

export interface CapsuleRiskBudgetMetrics {
  status?: string;
  survival_probability?: number;
  data_integrity_probability?: number;
  loss_probability?: number;
  margin?: number;
}

export interface CapsuleRiskBudgetContribution {
  driver?: string;
  label?: string;
  name?: string;
  mode?: string;
  share?: number;
  sensitivity?: number;
  contribution?: number;
  direction?: string;
  note?: string;
  source_ref?: string;
}

export interface CapsuleRiskBudgetImprovement {
  label?: string;
  name?: string;
  target_p50?: number;
  achieved?: boolean;
  threshold?: string;
  rationale?: string;
  status?: string;
  evidence_needed?: string;
}

export interface CapsuleRiskBudgetRow {
  rowId?: string;
  row_id?: string;
  capsuleRowId?: string;
  capsule_row_id?: string;
  attackModeId?: string;
  attack_mode_id?: string;
  mode_id?: string;
  monteCarlo?: CapsuleMonteCarloInterval;
  monte_carlo?: CapsuleMonteCarloInterval;
  monteCarloInterval?: CapsuleMonteCarloInterval;
  monte_carlo_interval?: CapsuleMonteCarloInterval;
  riskBudget?: CapsuleRiskBudgetMetrics;
  risk_budget?: CapsuleRiskBudgetMetrics;
  top_uncertainty_drivers?: CapsuleRiskBudgetContribution[];
  uncertaintyDrivers?: CapsuleRiskBudgetContribution[];
  uncertainty_drivers?: CapsuleRiskBudgetContribution[];
  failureModeContributions?: CapsuleRiskBudgetContribution[];
  failure_mode_contributions?: CapsuleRiskBudgetContribution[];
  required_improvement?: CapsuleRiskBudgetImprovement[];
  requiredImprovements?: CapsuleRiskBudgetImprovement[];
  required_improvements?: CapsuleRiskBudgetImprovement[];
  qualificationRoadmap?: CapsuleRiskBudgetImprovement[];
  qualification_roadmap?: CapsuleRiskBudgetImprovement[];
  evidence_needed?: Array<Record<string, unknown>>;
  evidence_gap_ids?: string[];
  acceptance_criteria?: Array<Record<string, unknown>>;
  blocking_claims?: string[];
}

export interface CapsuleRiskBudgetArtifact {
  schema_version: "capsule_risk_budget.v1";
  non_certification_notice: true;
  source_artifact_ref?: string;
  sample_count?: number;
  source_policy?: Record<string, unknown>;
  failure_modes?: Array<Record<string, unknown>>;
  qualification_roadmap?: Array<Record<string, unknown>>;
  attack_modes?: CapsuleRiskBudgetAttackMode[] | CapsuleRiskBudgetAttackModeSet;
  risk_budgets?: CapsuleRiskBudgetRow[];
  rows?: CapsuleRiskBudgetRow[];
}

export interface CapsuleRiskBudgetSelection {
  capsuleRowId?: string;
  attackModeId?: string;
}

function optionMap(options: CapsuleControlOption[]): Map<string, CapsuleControlOption> {
  return new Map(options.map((option) => [option.id, option]));
}

export function buildCapsuleLookup(artifact: CapsuleSurvivabilityLabArtifact): CapsuleLookup {
  return {
    rowsById: new Map(artifact.rows.map((row) => [row.rowId, row])),
    options: {
      targetsById: optionMap(artifact.controls.targets),
      timeHorizonsById: optionMap(artifact.controls.timeHorizons),
      velocityBandsById: optionMap(artifact.controls.velocityBands),
      capsuleProfilesById: optionMap(artifact.controls.capsuleProfiles),
    },
  };
}

export function findCapsuleRows(
  rows: CapsuleSurvivalRow[],
  selection: CapsuleSelectionPatch,
): CapsuleSurvivalRow[] {
  return rows.filter((row) => {
    if (selection.targetId && row.targetId !== selection.targetId) {
      return false;
    }
    if (selection.timeId && row.timeId !== selection.timeId) {
      return false;
    }
    if (selection.velocityId && row.velocityId !== selection.velocityId) {
      return false;
    }
    if (selection.capsuleId && row.capsuleId !== selection.capsuleId) {
      return false;
    }
    return true;
  });
}

export function pickCapsuleRow(
  rows: CapsuleSurvivalRow[],
  current: CapsuleSurvivalRow,
  patch: CapsuleSelectionPatch,
): CapsuleSurvivalRow {
  const merged: CapsuleSelection = {
    targetId: patch.targetId ?? current.targetId,
    timeId: patch.timeId ?? current.timeId,
    velocityId: patch.velocityId ?? current.velocityId,
    capsuleId: patch.capsuleId ?? current.capsuleId,
  };

  const exact = findCapsuleRows(rows, merged)[0];
  if (exact) {
    return exact;
  }

  const patched = findCapsuleRows(rows, patch)[0];
  return patched ?? current;
}

export function getUniqueCapsuleOptions<T extends CapsuleControlOption>(
  options: T[],
  rows: CapsuleSurvivalRow[],
  key: keyof CapsuleSelection,
): T[] {
  const available = new Set(rows.map((row) => row[key]));
  return options.filter((option) => available.has(option.id));
}

export function getCapsuleRiskBudgetRows(
  artifact: CapsuleRiskBudgetArtifact | undefined,
): CapsuleRiskBudgetRow[] {
  return artifact?.risk_budgets ?? artifact?.rows ?? [];
}

export function getCapsuleRiskBudgetRowCapsuleId(row: CapsuleRiskBudgetRow): string {
  return row.row_id ?? row.rowId ?? row.capsule_row_id ?? row.capsuleRowId ?? "";
}

export function getCapsuleRiskBudgetRowAttackModeId(row: CapsuleRiskBudgetRow): string {
  return row.attack_mode_id ?? row.attackModeId ?? row.mode_id ?? "";
}

function getAttackModeId(mode: CapsuleRiskBudgetAttackMode): string {
  return mode.attack_mode_id ?? mode.id ?? mode.mode_id ?? "";
}

function getAttackModes(artifact: CapsuleRiskBudgetArtifact | undefined): CapsuleRiskBudgetAttackMode[] {
  const attackModes = artifact?.attack_modes;
  if (Array.isArray(attackModes)) {
    return attackModes;
  }
  if (attackModes && Array.isArray(attackModes.modes)) {
    return attackModes.modes;
  }
  return [];
}

function readableModeLabel(id: string): string {
  return id.replaceAll("_", " ");
}

export function getCapsuleRiskBudgetAttackModes(
  artifact: CapsuleRiskBudgetArtifact | undefined,
  capsuleRowId?: string,
): CapsuleRiskBudgetModeOption[] {
  if (!artifact) {
    return [];
  }

  const rows = getCapsuleRiskBudgetRows(artifact);
  const availableModeIds = new Set(
    rows
      .filter((row) => !capsuleRowId || getCapsuleRiskBudgetRowCapsuleId(row) === capsuleRowId)
      .map((row) => getCapsuleRiskBudgetRowAttackModeId(row))
      .filter((id) => id !== ""),
  );
  const options: CapsuleRiskBudgetModeOption[] = [];
  const seen = new Set<string>();

  for (const mode of getAttackModes(artifact)) {
    const id = getAttackModeId(mode);
    if (!id || seen.has(id)) {
      continue;
    }
    if (availableModeIds.size > 0 && !availableModeIds.has(id)) {
      continue;
    }
    seen.add(id);
    options.push({
      id,
      label: mode.label ?? readableModeLabel(id),
      detail: mode.detail ?? mode.description,
    });
  }

  for (const modeId of availableModeIds) {
    if (seen.has(modeId)) {
      continue;
    }
    seen.add(modeId);
    options.push({
      id: modeId,
      label: readableModeLabel(modeId),
    });
  }

  return options;
}

export function findCapsuleRiskBudgetRows(
  artifact: CapsuleRiskBudgetArtifact | undefined,
  selection: CapsuleRiskBudgetSelection,
): CapsuleRiskBudgetRow[] {
  return getCapsuleRiskBudgetRows(artifact).filter((row) => {
    if (selection.capsuleRowId && getCapsuleRiskBudgetRowCapsuleId(row) !== selection.capsuleRowId) {
      return false;
    }
    if (selection.attackModeId && getCapsuleRiskBudgetRowAttackModeId(row) !== selection.attackModeId) {
      return false;
    }
    return true;
  });
}

export function pickCapsuleRiskBudgetRow(
  artifact: CapsuleRiskBudgetArtifact | undefined,
  selection: CapsuleRiskBudgetSelection,
): CapsuleRiskBudgetRow | undefined {
  const exact = findCapsuleRiskBudgetRows(artifact, selection)[0];
  if (exact) {
    return exact;
  }

  if (selection.capsuleRowId) {
    const sameCapsuleRow = findCapsuleRiskBudgetRows(artifact, { capsuleRowId: selection.capsuleRowId })[0];
    if (sameCapsuleRow) {
      return sameCapsuleRow;
    }
  }

  if (selection.attackModeId) {
    const sameMode = findCapsuleRiskBudgetRows(artifact, { attackModeId: selection.attackModeId })[0];
    if (sameMode) {
      return sameMode;
    }
  }

  return getCapsuleRiskBudgetRows(artifact)[0];
}
