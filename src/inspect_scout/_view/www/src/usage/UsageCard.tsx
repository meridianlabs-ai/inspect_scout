import { FC } from "react";

import { Card, CardBody, CardHeader } from "../components/Card";
import { ModelUsage } from "../types/api-types";

import { ModelTokenTable } from "./ModelTokenTable";
import styles from "./UsageCard.module.css";

const kUsageCardBodyId = "usage-card-body";

interface UsageCardProps {
  usage?: ModelUsage;
}

/**
 * Renders the UsageCard component.
 */
export const UsageCard: FC<UsageCardProps> = ({ usage }) => {
  if (!usage) {
    return null;
  }

  return (
    <Card>
      <CardHeader label="Usage" />
      <CardBody id={kUsageCardBodyId}>
        <div className={styles.wrapper}>
          <div className={styles.col2}>
            <ModelTokenTable model_usage={usage} />
          </div>
        </div>
      </CardBody>
    </Card>
  );
};
