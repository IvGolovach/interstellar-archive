import { useEffect, useMemo, useState } from "react";
import type { ParamCategory } from "../../../sim/public/types";
import type { SchemaField } from "../lib/schema_loader";

interface SchemaFormProps {
  fields: SchemaField[];
  params: Record<string, number>;
  clock: Record<string, number>;
  nonPhysicalChanged: boolean;
  onParamChange: (fieldId: string, value: number) => void;
  onClockChange: (fieldId: string, value: number) => void;
}

const CATEGORY_ORDER: ParamCategory[] = ["safe", "advanced", "non_physical"];

const CATEGORY_LABELS: Record<ParamCategory, string> = {
  safe: "Safe",
  advanced: "Advanced",
  non_physical: "Non-physical",
};

function labelize(fieldId: string): string {
  return fieldId
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function inferStep(field: SchemaField): number {
  const span = field.maximum - field.minimum;
  if (span <= 1) {
    return 0.001;
  }
  if (span <= 10) {
    return 0.01;
  }
  return 0.1;
}

export function SchemaForm(props: SchemaFormProps): JSX.Element {
  const { fields, params, clock, nonPhysicalChanged, onParamChange, onClockChange } = props;
  const [expanded, setExpanded] = useState<Record<ParamCategory, boolean>>({
    safe: true,
    advanced: false,
    non_physical: false,
  });

  useEffect(() => {
    if (nonPhysicalChanged) {
      setExpanded((current) => ({ ...current, non_physical: true }));
    }
  }, [nonPhysicalChanged]);

  const grouped = useMemo(() => {
    const groups: Record<ParamCategory, SchemaField[]> = {
      safe: [],
      advanced: [],
      non_physical: [],
    };
    for (const field of fields) {
      groups[field.category].push(field);
    }
    return groups;
  }, [fields]);

  return (
    <section>
      <h2>Parameters</h2>
      {nonPhysicalChanged ? (
        <p className="warning-banner top-warning-banner">
          Non-physical knobs are active. Results are exploratory and should not be interpreted as physically realistic.
        </p>
      ) : null}
      {CATEGORY_ORDER.map((category) => {
        const categoryFields = grouped[category];
        if (categoryFields.length === 0) {
          return null;
        }

        return (
          <div
            key={category}
            className={`category-block${category === "non_physical" ? " category-warning" : ""}`}
          >
            <button
              className="section-toggle"
              type="button"
              onClick={() => setExpanded((current) => ({ ...current, [category]: !current[category] }))}
            >
              <span>{CATEGORY_LABELS[category]}</span>
              <span>{expanded[category] ? "Hide" : "Show"}</span>
            </button>
            {expanded[category] ? (
              <>
                {category === "non_physical" ? (
                  <p className="warning-banner">
                    Non-physical knobs break realism; use for sensitivity exploration only.
                  </p>
                ) : null}
                <div className="field-grid">
                  {categoryFields.map((field) => {
                    const value = field.scope === "params" ? params[field.id] : clock[field.id];
                    const onChange = (raw: string) => {
                      const parsed = Number(raw);
                      if (field.scope === "params") {
                        onParamChange(field.id, parsed);
                        return;
                      }
                      onClockChange(field.id, parsed);
                    };

                    return (
                      <label key={`${category}-${field.scope}-${field.id}`} className="field">
                        <span>
                          {labelize(field.id)} ({field.unit})
                        </span>
                        <input
                          type="number"
                          value={value}
                          min={field.minimum}
                          max={field.maximum}
                          step={inferStep(field)}
                          onChange={(event) => onChange(event.target.value)}
                        />
                        <small>{field.help}</small>
                        {field.warning ? <strong>{field.warning}</strong> : null}
                      </label>
                    );
                  })}
                </div>
              </>
            ) : null}
          </div>
        );
      })}
    </section>
  );
}
