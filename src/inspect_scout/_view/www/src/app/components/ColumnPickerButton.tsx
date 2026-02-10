import { clsx } from "clsx";
import { FC, ReactNode, useRef, useState } from "react";

import { ApplicationIcons } from "../../components/icons";
import { ToolButton } from "../../components/ToolButton";

import styles from "./FilterBar.module.css";

export interface ColumnPickerRenderProps {
  positionEl: HTMLButtonElement | null;
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
}

export interface ColumnPickerButtonProps {
  /**
   * Render prop for the popover content.
   * Receives positionEl, isOpen, and setIsOpen to wire up the popover.
   */
  children: (props: ColumnPickerRenderProps) => ReactNode;
}

/**
 * Column picker button pattern extracted for reuse.
 * Manages button ref and open/closed state internally.
 * Uses render prop pattern to allow domain-specific popovers.
 */
export const ColumnPickerButton: FC<ColumnPickerButtonProps> = ({
  children,
}) => {
  const buttonRef = useRef<HTMLButtonElement>(null);
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <ToolButton
        ref={buttonRef}
        icon={ApplicationIcons.checkbox.checked}
        label="Choose columns"
        title="Choose columns"
        latched={isOpen}
        onClick={() => setIsOpen(!isOpen)}
        subtle
        className={clsx("text-size-smallest", styles.columnsButton)}
      />
      {children({
        // eslint-disable-next-line react-hooks/refs -- positionEl accepts null; PopOver/Popper handles this in effects and updates when ref is populated
        positionEl: buttonRef.current,
        isOpen,
        setIsOpen,
      })}
    </>
  );
};
