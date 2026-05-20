import type {
  DynamicStaticValidationResult,
  DynamicTraceIndex,
  FailureSurfaceBaseline,
  ObjectiveContract,
  ObjectiveScoreBaseline,
  OptimizationFrontierArtifact,
  ParameterEvidenceEntry,
  ParameterManifestEntry,
  PSuccessDefensibility,
  ParameterStaticUsageEntry,
} from "../../lib/parameter_drilldown_loader";
import { VisualizationLayerPanel } from "../visualization/VisualizationLayerPanel";
import { ObjectiveContractPanel } from "./ObjectiveContractPanel";
import { ParameterDefinitionSection } from "./ParameterDefinitionSection";
import { ParameterDerivedSections } from "./ParameterDerivedSections";
import { ParameterDetailHeader } from "./ParameterDetailHeader";
import { ParameterDynamicUsageSection } from "./ParameterDynamicUsageSection";
import { ParameterEvidenceSection } from "./ParameterEvidenceSection";
import { ParameterScientificBasisSection } from "./ParameterScientificBasisSection";
import { ParameterStaticUsageSection } from "./ParameterStaticUsageSection";
import { dynamicEventsForParameter } from "./parameter_drilldown_helpers";

interface ParameterDetailPageProps {
  parameter: ParameterManifestEntry | null;
  evidenceEntry: ParameterEvidenceEntry | null;
  staticUsageEntry: ParameterStaticUsageEntry | null;
  pSuccessDefensibility: PSuccessDefensibility;
  failureSurfaceBaseline: FailureSurfaceBaseline;
  objectiveContract: ObjectiveContract;
  objectiveScoreBaseline: ObjectiveScoreBaseline;
  optimizationFrontier: OptimizationFrontierArtifact;
  onBack: () => void;
  devLocalEnabled: boolean;
  dynamicTrace: DynamicTraceIndex | null;
  dynamicValidation: DynamicStaticValidationResult | null;
  dynamicTraceLoadError: string | null;
  onLoadDynamicTraceFile: (file: File) => Promise<void>;
}

export function ParameterDetailPage(props: ParameterDetailPageProps): JSX.Element {
  const {
    parameter,
    evidenceEntry,
    staticUsageEntry,
    pSuccessDefensibility,
    failureSurfaceBaseline,
    objectiveContract,
    objectiveScoreBaseline,
    optimizationFrontier,
    onBack,
    devLocalEnabled,
    dynamicTrace,
    dynamicValidation,
    dynamicTraceLoadError,
    onLoadDynamicTraceFile,
  } = props;

  if (!parameter) {
    return (
      <section className="panel drilldown-panel">
        <h2>Parameter Detail</h2>
        <p className="error-text">Parameter not found in manifest.</p>
        <button className="ghost-button" type="button" onClick={onBack}>
          Back to Parameter Index
        </button>
      </section>
    );
  }

  const dynamicEvents = dynamicTrace
    ? dynamicEventsForParameter(dynamicTrace, parameter.parameter_id)
    : [];

  return (
    <section className="panel drilldown-panel" aria-label="Parameter drilldown detail">
      <ParameterDetailHeader parameterId={parameter.parameter_id} onBack={onBack} />

      <ParameterDefinitionSection parameter={parameter} />

      <ParameterStaticUsageSection
        parameter={parameter}
        staticUsageEntry={staticUsageEntry}
      />

      <ParameterEvidenceSection parameter={parameter} evidenceEntry={evidenceEntry} />

      <ParameterScientificBasisSection
        parameter={parameter}
        evidenceEntry={evidenceEntry}
        pSuccessDefensibility={pSuccessDefensibility}
      />

      <ParameterDerivedSections parameter={parameter} />

      <VisualizationLayerPanel
        failureSurfaceBaseline={failureSurfaceBaseline}
        optimizationFrontier={optimizationFrontier}
        objectiveScoreBaseline={objectiveScoreBaseline}
      />
      <ObjectiveContractPanel
        contract={objectiveContract}
        baselineScore={objectiveScoreBaseline}
      />

      {devLocalEnabled ? (
        <ParameterDynamicUsageSection
          dynamicEvents={dynamicEvents}
          dynamicTrace={dynamicTrace}
          dynamicTraceLoadError={dynamicTraceLoadError}
          dynamicValidation={dynamicValidation}
          onLoadDynamicTraceFile={onLoadDynamicTraceFile}
        />
      ) : null}
    </section>
  );
}
