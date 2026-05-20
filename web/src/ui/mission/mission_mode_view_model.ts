import type {
  MissionControlPanelModel,
  MissionField,
  MissionFieldBinding,
  MissionModeOverviewModel,
  MissionOptimizationPanelModel,
  MissionResultsPanelModel,
} from "./mission_mode_contract";

export function bindMissionFields(args: {
  baselineClock: Record<string, number>;
  baselineParams: Record<string, number>;
  clock: Record<string, number>;
  fields: MissionField[];
  onClockChange: (fieldId: string, value: number) => void;
  onParamsChange: (fieldId: string, value: number) => void;
  params: Record<string, number>;
}): MissionFieldBinding[] {
  const {
    baselineClock,
    baselineParams,
    clock,
    fields,
    onClockChange,
    onParamsChange,
    params,
  } = args;

  return fields.map((field) => ({
    baseValue: field.scope === "params" ? baselineParams[field.id] : baselineClock[field.id],
    currentValue: field.scope === "params" ? params[field.id] : clock[field.id],
    field,
    onValueChange: field.scope === "params" ? onParamsChange : onClockChange,
  }));
}

export function buildMissionControlPanelModel(
  model: MissionControlPanelModel,
): MissionControlPanelModel {
  return model;
}

export function buildMissionModeOverviewModel(
  model: MissionModeOverviewModel,
): MissionModeOverviewModel {
  return model;
}

export function buildMissionResultsPanelModel(
  model: MissionResultsPanelModel,
): MissionResultsPanelModel {
  return model;
}

export function buildMissionOptimizationPanelModel(
  model: MissionOptimizationPanelModel,
): MissionOptimizationPanelModel {
  return model;
}
