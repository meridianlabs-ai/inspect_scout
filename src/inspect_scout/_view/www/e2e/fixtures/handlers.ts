import { http, HttpResponse } from "msw";

import {
  createActiveScansResponse,
  createAppConfig,
  createMessagesEventsResponse,
  createProjectConfig,
  createScansResponse,
  createStatus,
  createTranscriptInfo,
  createTranscriptsResponse,
} from "./test-data";

/** Default handlers that let the app boot cleanly. */
export const defaultHandlers = [
  http.get("/api/v2/app-config", () => {
    return HttpResponse.json(createAppConfig());
  }),

  http.post("/api/v2/transcripts/:dir", () => {
    return HttpResponse.json(createTranscriptsResponse());
  }),

  http.post("/api/v2/scans/:dir", () => {
    return HttpResponse.json(createScansResponse());
  }),

  http.get("/api/v2/scans/active", () => {
    return HttpResponse.json(createActiveScansResponse());
  }),

  http.post("/api/v2/transcripts/:dir/distinct", () => {
    return HttpResponse.json([]);
  }),

  http.post("/api/v2/scans/:dir/distinct", () => {
    return HttpResponse.json([]);
  }),

  http.get("/api/v2/validations", () => {
    return HttpResponse.json([]);
  }),

  http.get("/api/v2/project/config", () => {
    return HttpResponse.json(createProjectConfig(), {
      headers: { ETag: '"e2e-etag-1"' },
    });
  }),

  // Detail panel defaults (prevent unhandled requests during unrelated tests)
  http.get("/api/v2/scans/:dir/:scanPath", () => {
    return HttpResponse.json(createStatus());
  }),

  http.get("/api/v2/transcripts/:dir/:id/info", () => {
    return HttpResponse.json(
      createTranscriptInfo({ transcript_id: "default" }),
    );
  }),

  http.get("/api/v2/transcripts/:dir/:id/messages-events", () => {
    return HttpResponse.json(createMessagesEventsResponse());
  }),
];
