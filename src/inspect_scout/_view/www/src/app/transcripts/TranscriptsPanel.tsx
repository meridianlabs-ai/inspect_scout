import clsx from "clsx";
import { FC } from "react";

import { ErrorPanel } from "../../components/ErrorPanel";
import { useStore } from "../../state/store";
import { Footer } from "../components/Footer";
import { TranscriptsNavbar } from "../components/TranscriptsNavbar";
import { useServerTranscripts } from "../server/hooks";

import { TranscriptsGrid } from "./TranscriptsList";
import styles from "./TranscriptsPanel.module.css";

export const TranscriptsPanel: FC = () => {
  useServerTranscripts();

  const transcripts = useStore((state) => state.transcripts);
  const error = useStore((state) => state.scopedErrors["transcripts"]);

  return (
    <div className={clsx(styles.container)}>
      <TranscriptsNavbar bordered={true} />
      {error && (
        <ErrorPanel
          title="Error Loading Transcript"
          error={{ message: error }}
        />
      )}
      {!error && <TranscriptsGrid transcripts={transcripts} />}
      <Footer
        itemCount={transcripts?.length || 0}
        id={"transcripts-footer"}
        paginated={false}
      />
    </div>
  );
};
