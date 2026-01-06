import clsx from "clsx";
import { FC } from "react";

import { ApplicationIcons } from "../../components/icons";

import styles from "./Error.module.css";

interface ErrorProps {
  error: string;
  refusal?: boolean;
}

export const Error: FC<ErrorProps> = ({ error, refusal }) => {
  const icon = refusal ? ApplicationIcons.refuse : ApplicationIcons.error;
  const message = refusal ? "Refusal" : error;
  return (
    <div className={clsx(styles.error, refusal && styles.refusal)}>
      <i className={clsx(icon)} />
      {message}
    </div>
  );
};
