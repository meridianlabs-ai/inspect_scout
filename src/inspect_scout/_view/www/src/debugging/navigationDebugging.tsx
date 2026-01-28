import { useMemo } from "react";
import {
  Navigate,
  NavigateOptions,
  NavigateProps,
  To,
  useNavigate,
  useLocation,
  NavigateFunction,
} from "react-router-dom";

const NAVIGATION_LOGGING_ENABLED = false;

export const timestamp = () => new Date().toISOString().slice(11, 23);

type LoggingNavigateProps = NavigateProps & { reason: string };

export const LoggingNavigate = ({ reason, ...props }: LoggingNavigateProps) => {
  const location = useLocation();
  if (NAVIGATION_LOGGING_ENABLED) {
    console.log(
      `[${timestamp()}] <Navigate /> ('${reason}') navigating\n\twindow.location.hash='${window.location.hash}'\n\trouter.location='${location.pathname}'\nto\n\t${JSON.stringify(props.to)}`
    );
  }
  return <Navigate {...props} />;
};

export const useLoggingNavigate = (description: string): NavigateFunction => {
  const navigate = useNavigate();
  const location = useLocation();
  return useMemo(
    () => wrapNavigate(navigate, description, location),
    [navigate, description, location]
  );
};

const wrapNavigate = (
  navigate: NavigateFunction,
  description: string,
  location: ReturnType<typeof useLocation>
): NavigateFunction => {
  function loggingNavigate(
    to: To,
    options?: NavigateOptions
  ): void | Promise<void>;
  function loggingNavigate(delta: number): void | Promise<void>;
  function loggingNavigate(
    toOrDelta: To | number,
    options?: NavigateOptions
  ): void | Promise<void> {
    if (NAVIGATION_LOGGING_ENABLED) {
      console.log(
        `[${timestamp()}] navigate() ('${description}')\n\twindow.location.hash='${window.location.hash}'\n\trouter location: pathname='${location.pathname}' hash='${location.hash}'\nto\n\t${JSON.stringify(toOrDelta)}`
      );
    }
    if (typeof toOrDelta === "number") {
      return navigate(toOrDelta);
    } else {
      return navigate(toOrDelta, options);
    }
  }
  return loggingNavigate;
};
