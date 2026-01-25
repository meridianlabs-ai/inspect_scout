import {
  VscodeRadio,
  VscodeRadioGroup,
  VscodeTextfield,
} from "@vscode-elements/react-elements";
import { FC, useEffect, useState } from "react";

import { JsonValue } from "../../../types/api-types";

type TargetMode = "true" | "false" | "other" | "unset";

function getInitialMode(target?: JsonValue): TargetMode {
  if (target === undefined) {
    return "unset";
  }
  if (target === "true" || target === true) {
    return "true";
  }
  if (target === "false" || target === false) {
    return "false";
  }
  return "other";
}

interface ValidationCaseTargetEditorProps {
  target?: JsonValue;
  onChange: (newTarget: string) => void;
}

/**
 * Editor component for modifying the target of a validation case.
 */
export const ValidationCaseTargetEditor: FC<
  ValidationCaseTargetEditorProps
> = ({ target, onChange }) => {
  const [mode, setMode] = useState<TargetMode>(() => getInitialMode(target));

  useEffect(() => {
    setMode(getInitialMode(target));
  }, [target, setMode]);

  const [customValue, setCustomValue] = useState(() => {
    return getInitialMode(target) === "other" ? String(target ?? "") : "";
  });
  useEffect(() => {
    if (getInitialMode(target) === "other") {
      setCustomValue(String(target ?? ""));
    }
  }, [target, setCustomValue]);

  const handleRadioChange = (value: string) => {
    const newMode = value as TargetMode;
    setMode(newMode);

    if (newMode === "other") {
      onChange(customValue);
    } else {
      onChange(newMode);
    }
  };

  const handleCustomValueChange = (value: string) => {
    setCustomValue(value);
    onChange(value);
  };

  return (
    <div>
      <VscodeRadioGroup
        onChange={(e) =>
          handleRadioChange((e.target as HTMLInputElement).value)
        }
      >
        <VscodeRadio label="True" value="true" checked={mode === "true"} />
        <VscodeRadio label="False" value="false" checked={mode === "false"} />
        <VscodeRadio label="Other" value="other" checked={mode === "other"} />
      </VscodeRadioGroup>

      {mode === "other" && (
        <VscodeTextfield
          value={customValue}
          placeholder="Enter target value"
          onInput={(e) =>
            handleCustomValueChange((e.target as HTMLInputElement).value)
          }
          style={{ marginTop: "8px" }}
        />
      )}
    </div>
  );
};
