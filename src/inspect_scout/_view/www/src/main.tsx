import { createRoot } from "react-dom/client";
import { App } from "./App";
import "bootstrap/dist/css/bootstrap.min.css";
import "bootstrap-icons/font/bootstrap-icons.css";

// Find the root element and render into it
const containerId = "app";
const container = document.getElementById(containerId);
if (!container) {
  console.error("Root container not found");
  throw new Error(
    `Expected a container element with Id '${containerId}' but no such container element was present.`,
  );
}

// Render into the root
const root = createRoot(container as HTMLElement);
root.render(<App />);
