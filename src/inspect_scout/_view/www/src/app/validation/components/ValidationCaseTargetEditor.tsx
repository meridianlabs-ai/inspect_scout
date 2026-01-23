import { VscodeRadioGroup, VscodeRadio } from "@vscode-elements/react-elements";
import { FC } from "react";

import { JsonValue } from "../../../types/api-types";

interface ValidationCaseTargetEditorProps {
  target: JsonValue;
  onChange: (newTarget: string) => void;
}

/**
 * Editor component for modifying the target of a validation case.
 */
export const ValidationCaseTargetEditor: FC<
  ValidationCaseTargetEditorProps
> = ({ target, onChange }) => {
  return (
    <VscodeRadioGroup
      onChange={(e) => onChange((e.target as HTMLInputElement).value)}
    >
      <VscodeRadio label="True" value="true" checked={target === "true"} />
      <VscodeRadio label="False" value="false" checked={target === "false"} />
      <VscodeRadio label="Other" value="other" checked={target === "other"} />
    </VscodeRadioGroup>
  );
};
