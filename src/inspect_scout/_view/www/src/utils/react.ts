import { useEffect, useRef } from "react";

/**
 * Stable empty object reference to avoid unnecessary re-renders.
 * Use as a default value when a nullable object prop needs a fallback.
 */
export const STABLE_EMPTY_OBJECT: Record<string, never> = {};

export const useWhyDidYouUpdate = (componentName: string, props: any) => {
  const previousProps = useRef(props);

  useEffect(() => {
    if (previousProps.current !== props) {
      const changedProps = Object.entries(props).reduce(
        (diff, [key, value]) => {
          if (previousProps.current[key] !== value) {
            diff[key] = {
              before: previousProps.current[key],
              after: value,
            };
          }
          return diff;
        },
        {} as Record<string, unknown>
      );

      if (Object.keys(changedProps).length > 0) {
        console.log(`[${componentName}] props changed:`, changedProps);
      } else {
        console.log(`[${componentName}] no props changed`);
      }
    }

    previousProps.current = props;
  }, [props, componentName]);
};
