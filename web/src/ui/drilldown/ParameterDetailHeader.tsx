interface ParameterDetailHeaderProps {
  parameterId: string;
  onBack: () => void;
}

export function ParameterDetailHeader(props: ParameterDetailHeaderProps): JSX.Element {
  const { parameterId, onBack } = props;

  return (
    <div className="drilldown-detail-header">
      <div>
        <h2>Parameter Detail</h2>
        <p className="mono-cell">{parameterId}</p>
      </div>
      <button className="ghost-button" type="button" onClick={onBack}>
        Back to Parameter Index
      </button>
    </div>
  );
}
