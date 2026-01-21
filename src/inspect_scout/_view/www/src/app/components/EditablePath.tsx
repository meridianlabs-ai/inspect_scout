import { FC } from "react";

import { isUri, prettyDirUri } from "../../utils/uri";

import { EditableText } from "./EditableText";

interface EditablePathProps {
  path?: string | null;
  onPathChanged: (path: string) => void;

  mru?: string[];

  label?: string;
  title?: string;

  icon?: string;
  placeholder?: string;

  editable?: boolean;

  className?: string;
}

export const EditablePath: FC<EditablePathProps> = ({
  path,
  onPathChanged,
  mru,
  label,
  title,
  icon,
  placeholder,
  editable = true,
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
      mru={mru}
      label={label}
      title={title}
      icon={icon}
      placeholder={placeholder}
      className={className}
      editable={editable}
    />
  );
};
