// @vitest-environment jsdom
import { skipToken } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse, passthrough } from "msw";
import { beforeAll, expect, it } from "vitest";
import { ZstdCodec } from "zstd-codec";

import { server } from "../../test/setup-msw";
import { createTestWrapper } from "../../test/test-utils";
import { MessagesEventsResponse, TranscriptInfo } from "../../types/api-types";
import { encodeBase64Url } from "../../utils/base64url";

import { useTranscript } from "./useTranscript";

// Initialize zstd compression for tests
let compressZstd: (data: Uint8Array) => Uint8Array;

beforeAll(async () => {
  // zstd-codec loads WASM via a data URL that MSW intercepts. Passthrough
  // prevents MSW from erroring on this unhandled request.
  server.use(http.get(/octet-stream;base64,/, () => passthrough()));

  await new Promise<void>((resolve) => {
    ZstdCodec.run((zstd) => {
      const simple = new zstd.Simple();
      compressZstd = (data: Uint8Array) => simple.compress(data);
      resolve();
    });
  });
});

const location = "/transcripts";
const encodedLocation = encodeBase64Url(location);
const transcriptId = "sample-transcript-id";
const encodedId = encodeURIComponent(transcriptId);

const mockTranscriptInfo: TranscriptInfo = {
  metadata: { task: "test-task" },
  model: "gpt-4",
  date: "2025-01-15T10:00:00Z",
  message_count: 5,
  source_id: "test-source",
  source_type: "eval",
  source_uri: "/path/to/source.eval",
  task_id: "test-task",
  transcript_id: "test-uuid-123",
};

const mockMessagesEvents: MessagesEventsResponse = {
  messages: [
    {
      role: "user",
      content: "Hello",
      id: null,
      metadata: null,
      source: null,
      tool_call_id: null,
    },
    {
      role: "assistant",
      content: "Hi there!",
      id: null,
      metadata: null,
      model: null,
      source: null,
      tool_calls: null,
    },
  ],
  events: [
    {
      event: "info",
      timestamp: "2025-01-15T10:00:00Z",
      data: { sample: true },
      metadata: null,
      pending: null,
      source: null,
      span_id: null,
      uuid: null,
      working_start: 0,
    },
  ],
};

function setupInfoHandler(): void {
  server.use(
    http.get(`/api/v2/transcripts/${encodedLocation}/${encodedId}/info`, () =>
      HttpResponse.json<TranscriptInfo>(mockTranscriptInfo)
    )
  );
}

function setupMessagesEventsJsonHandler(): void {
  server.use(
    http.get(
      `/api/v2/transcripts/${encodedLocation}/${encodedId}/messages-events`,
      () => HttpResponse.json<MessagesEventsResponse>(mockMessagesEvents)
    )
  );
}

function setupMessagesEventsZstdHandler(): void {
  server.use(
    http.get(
      `/api/v2/transcripts/${encodedLocation}/${encodedId}/messages-events`,
      () => {
        const jsonString = JSON.stringify(mockMessagesEvents);
        const encoder = new TextEncoder();
        const uncompressed = encoder.encode(jsonString);
        const compressed = compressZstd(uncompressed);

        return new HttpResponse(compressed, {
          status: 200,
          headers: {
            "Content-Type": "application/octet-stream",
            "X-Content-Encoding": "zstd",
          },
        });
      }
    )
  );
}

it("returns loading then data on successful JSON fetch", async () => {
  setupInfoHandler();
  setupMessagesEventsJsonHandler();

  const { result } = renderHook(
    () => useTranscript({ location, id: transcriptId }),
    { wrapper: createTestWrapper() }
  );

  expect(result.current.loading).toBe(true);

  await waitFor(() => {
    expect(result.current.loading).toBe(false);
  });

  expect(result.current.error).toBeUndefined();
  expect(result.current.data).toBeDefined();
  expect(result.current.data?.model).toBe("gpt-4");
  expect(result.current.data?.messages).toHaveLength(2);
  expect(result.current.data?.events).toHaveLength(1);
});

it("returns loading then data on successful zstd fetch", async () => {
  setupInfoHandler();
  setupMessagesEventsZstdHandler();

  const { result } = renderHook(
    () => useTranscript({ location, id: transcriptId }),
    { wrapper: createTestWrapper() }
  );

  expect(result.current.loading).toBe(true);

  await waitFor(() => {
    expect(result.current.loading).toBe(false);
  });

  expect(result.current.error).toBeUndefined();
  expect(result.current.data).toBeDefined();
  expect(result.current.data?.model).toBe("gpt-4");
  expect(result.current.data?.messages).toHaveLength(2);
  expect(result.current.data?.events).toHaveLength(1);
});

it("does not make request when skipToken is passed", async () => {
  let infoRequestMade = false;
  let messagesEventsRequestMade = false;

  server.use(
    http.get(`/api/v2/transcripts/${encodedLocation}/${encodedId}/info`, () => {
      infoRequestMade = true;
      return HttpResponse.json<TranscriptInfo>(mockTranscriptInfo);
    }),
    http.get(
      `/api/v2/transcripts/${encodedLocation}/${encodedId}/messages-events`,
      () => {
        messagesEventsRequestMade = true;
        return HttpResponse.json<MessagesEventsResponse>(mockMessagesEvents);
      }
    )
  );

  const { result } = renderHook(() => useTranscript(skipToken), {
    wrapper: createTestWrapper(),
  });

  expect(result.current.loading).toBe(true);

  await new Promise((r) => setTimeout(r, 50));
  expect(infoRequestMade).toBe(false);
  expect(messagesEventsRequestMade).toBe(false);
});

it("returns error when info endpoint fails", async () => {
  server.use(
    http.get(`/api/v2/transcripts/${encodedLocation}/${encodedId}/info`, () =>
      HttpResponse.text("Server Error", { status: 500 })
    ),
    http.get(
      `/api/v2/transcripts/${encodedLocation}/${encodedId}/messages-events`,
      () => HttpResponse.json<MessagesEventsResponse>(mockMessagesEvents)
    )
  );

  const { result } = renderHook(
    () => useTranscript({ location, id: transcriptId }),
    { wrapper: createTestWrapper() }
  );

  await waitFor(() => {
    expect(result.current.loading).toBe(false);
  });

  expect(result.current.error).toBeDefined();
  expect(result.current.error?.message).toContain("500");
});

it("returns error when messages-events endpoint fails", async () => {
  setupInfoHandler();
  server.use(
    http.get(
      `/api/v2/transcripts/${encodedLocation}/${encodedId}/messages-events`,
      () => HttpResponse.text("Server Error", { status: 500 })
    )
  );

  const { result } = renderHook(
    () => useTranscript({ location, id: transcriptId }),
    { wrapper: createTestWrapper() }
  );

  await waitFor(() => {
    expect(result.current.loading).toBe(false);
  });

  expect(result.current.error).toBeDefined();
  expect(result.current.error?.message).toContain("500");
});

it("returns error for unsupported X-Content-Encoding", async () => {
  setupInfoHandler();
  server.use(
    http.get(
      `/api/v2/transcripts/${encodedLocation}/${encodedId}/messages-events`,
      () => {
        return new HttpResponse("some data", {
          status: 200,
          headers: {
            "Content-Type": "application/octet-stream",
            "X-Content-Encoding": "unsupported-encoding",
          },
        });
      }
    )
  );

  const { result } = renderHook(
    () => useTranscript({ location, id: transcriptId }),
    { wrapper: createTestWrapper() }
  );

  await waitFor(() => {
    expect(result.current.loading).toBe(false);
  });

  expect(result.current.error).toBeDefined();
  expect(result.current.error?.message).toContain(
    "Unsupported X-Content-Encoding"
  );
});

it("handles attachments in messages-events response", async () => {
  const messagesWithAttachmentRefs: MessagesEventsResponse = {
    messages: [
      {
        role: "user",
        content: "See attachment: {{att:image1}}",
        id: null,
        metadata: null,
        source: null,
        tool_call_id: null,
      },
    ],
    events: [],
    attachments: {
      image1: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYA",
    },
  };

  setupInfoHandler();
  server.use(
    http.get(
      `/api/v2/transcripts/${encodedLocation}/${encodedId}/messages-events`,
      () =>
        HttpResponse.json<MessagesEventsResponse>(messagesWithAttachmentRefs)
    )
  );

  const { result } = renderHook(
    () => useTranscript({ location, id: transcriptId }),
    { wrapper: createTestWrapper() }
  );

  await waitFor(() => {
    expect(result.current.loading).toBe(false);
  });

  expect(result.current.error).toBeUndefined();
  expect(result.current.data).toBeDefined();
  expect(result.current.data?.messages).toHaveLength(1);
});

it("sends correct X-Accept-Raw-Encoding header", async () => {
  let capturedHeaders: Headers | undefined;

  setupInfoHandler();
  server.use(
    http.get(
      `/api/v2/transcripts/${encodedLocation}/${encodedId}/messages-events`,
      ({ request }) => {
        capturedHeaders = new Headers(request.headers);
        return HttpResponse.json<MessagesEventsResponse>(mockMessagesEvents);
      }
    )
  );

  const { result } = renderHook(
    () => useTranscript({ location, id: transcriptId }),
    { wrapper: createTestWrapper() }
  );

  await waitFor(() => {
    expect(result.current.loading).toBe(false);
  });

  expect(capturedHeaders?.get("X-Accept-Raw-Encoding")).toBe("zstd");
});
