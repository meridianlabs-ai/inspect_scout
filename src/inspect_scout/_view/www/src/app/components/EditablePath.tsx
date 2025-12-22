import { FC } from "react";

import { isUri, prettyDirUri } from "../../utils/uri";

import styles from "./EditablePath.module.css";
import { EditableText } from "./EditableText";

interface EditablePathProps {
  path?: string;
  onPathChanged: (path: string) => void;

  mru?: string[];

  icon?: string;
  placeholder?: string;

  className?: string;
}

export const EditablePath: FC<EditablePathProps> = ({
  path,
  onPathChanged,
  icon,
  placeholder,
  className,
}) => {
  // Format a local path without the file:// prefix
  const displayPath = prettyDirUri(path || "");

  const onValueChanged = (newDisplayPath: string) => {
    if (isUri(newDisplayPath)) {
      onPathChanged(newDisplayPath);
    } else {
      const newUri = `file://${newDisplayPath}`;
      onPathChanged(newUri);
    }
  };

  return (
    <EditableText
      value={displayPath}
      onValueChanged={onValueChanged}
      icon={icon}
      placeholder={placeholder}
      className={className}
    />
  );
};
