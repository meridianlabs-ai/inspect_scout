import { j as jsxRuntimeExports, c as clsx, r as reactExports, A as ApplicationIcons } from "./index.js";
import { d as VscodeSingleSelect, e as VscodeOption } from "./VscodeTreeItem.js";
import { l as useProperty, u as useEventNodes, T as TranscriptViewNodes } from "./TranscriptViewNodes.js";
import { u as useTimeline, c as computeTimeMapping, a as computeRowLayouts, g as getSelectedSpans, e as computeMinimapSelection, d as collectRawEvents, T as TimelineSwimLanes, f as TranscriptOutline } from "./timelineEventNodes.js";
import { u as useDocumentTitle } from "./useDocumentTitle.js";
import "./_commonjsHelpers.js";
import "./ToolButton.js";
import "./chunk-DfAF0w94.js";
import "./NoContentsPanel.js";
const pillRow = "_pillRow_1kmry_1";
const pill = "_pill_1kmry_1";
const pillActive = "_pillActive_1kmry_24";
const styles$1 = {
  pillRow,
  pill,
  pillActive
};
const TimelinePills = ({
  timelines,
  activeIndex,
  onSelect
}) => {
  if (timelines.length <= 1) return null;
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$1.pillRow, children: timelines.map((tl, i) => /* @__PURE__ */ jsxRuntimeExports.jsx(
    "button",
    {
      className: clsx(styles$1.pill, i === activeIndex && styles$1.pillActive),
      onClick: () => onSelect(i),
      title: tl.description,
      children: tl.name
    },
    i
  )) });
};
function ts(baseMs, offsetSeconds) {
  return new Date(baseMs + offsetSeconds * 1e3);
}
const BASE = (/* @__PURE__ */ new Date("2025-01-15T10:00:00Z")).getTime();
const NULL_CONFIG = {
  attempt_timeout: null,
  batch: null,
  best_of: null,
  cache: null,
  cache_prompt: null,
  effort: null,
  extra_body: null,
  extra_headers: null,
  frequency_penalty: null,
  internal_tools: null,
  logit_bias: null,
  logprobs: null,
  max_connections: null,
  max_retries: null,
  max_tokens: null,
  max_tool_output: null,
  num_choices: null,
  parallel_tool_calls: null,
  presence_penalty: null,
  reasoning_effort: null,
  reasoning_history: null,
  reasoning_summary: null,
  reasoning_tokens: null,
  response_schema: null,
  seed: null,
  stop_seqs: null,
  system_message: null,
  temperature: null,
  timeout: null,
  top_k: null,
  top_logprobs: null,
  top_p: null,
  verbosity: null
};
function makeModelEventNode(content2, startSec, endSec, tokens, uuid) {
  const event = {
    event: "model",
    model: "claude-sonnet-4-5-20250929",
    input: [],
    tools: [],
    tool_choice: "auto",
    config: NULL_CONFIG,
    output: {
      choices: [
        {
          message: {
            role: "assistant",
            content: content2,
            id: null,
            metadata: null,
            model: null,
            source: null,
            tool_calls: null
          },
          stop_reason: "stop",
          logprobs: null
        }
      ],
      completion: content2,
      error: null,
      metadata: null,
      model: "claude-sonnet-4-5-20250929",
      time: endSec - startSec,
      usage: {
        input_tokens: Math.floor(tokens * 0.6),
        output_tokens: Math.floor(tokens * 0.4),
        total_tokens: tokens,
        input_tokens_cache_read: null,
        input_tokens_cache_write: null,
        reasoning_tokens: null,
        total_cost: null
      }
    },
    timestamp: ts(BASE, startSec).toISOString(),
    working_start: startSec,
    working_time: endSec - startSec,
    cache: null,
    call: null,
    completed: null,
    error: null,
    metadata: null,
    pending: null,
    retries: null,
    role: null,
    span_id: null,
    traceback: null,
    traceback_ansi: null,
    uuid: uuid ?? null
  };
  return {
    type: "event",
    event,
    startTime: ts(BASE, startSec),
    endTime: ts(BASE, endSec),
    totalTokens: tokens,
    idleTime: 0
  };
}
function makeToolEventNode(fn, args, result, startSec, endSec, tokens) {
  const event = {
    event: "tool",
    type: "function",
    function: fn,
    id: `call-${fn}-${startSec}`,
    arguments: args,
    result,
    events: [],
    timestamp: ts(BASE, startSec).toISOString(),
    working_start: startSec,
    working_time: endSec - startSec,
    agent: null,
    completed: null,
    error: null,
    failed: null,
    message_id: null,
    metadata: null,
    pending: null,
    span_id: null,
    truncated: null,
    uuid: null,
    view: null
  };
  return {
    type: "event",
    event,
    startTime: ts(BASE, startSec),
    endTime: ts(BASE, endSec),
    totalTokens: tokens,
    idleTime: 0
  };
}
function makeToolErrorEventNode(fn, errorMsg, errorType, startSec, endSec, tokens) {
  const event = {
    event: "tool",
    type: "function",
    function: fn,
    id: `call-${fn}-${startSec}`,
    arguments: {},
    result: `Error: ${errorMsg}`,
    events: [],
    timestamp: ts(BASE, startSec).toISOString(),
    working_start: startSec,
    working_time: endSec - startSec,
    error: { message: errorMsg, type: errorType },
    failed: true,
    agent: null,
    completed: null,
    message_id: null,
    metadata: null,
    pending: null,
    span_id: null,
    truncated: null,
    uuid: null,
    view: null
  };
  return {
    type: "event",
    event,
    startTime: ts(BASE, startSec),
    endTime: ts(BASE, endSec),
    totalTokens: tokens,
    idleTime: 0
  };
}
function makeModelErrorEventNode(_content, errorMsg, startSec, endSec, tokens) {
  const event = {
    event: "model",
    model: "claude-sonnet-4-5-20250929",
    input: [],
    tools: [],
    tool_choice: "auto",
    config: NULL_CONFIG,
    output: {
      choices: [],
      completion: "",
      error: errorMsg,
      metadata: null,
      model: "claude-sonnet-4-5-20250929",
      time: endSec - startSec,
      usage: {
        input_tokens: Math.floor(tokens * 0.8),
        output_tokens: Math.floor(tokens * 0.2),
        total_tokens: tokens,
        input_tokens_cache_read: null,
        input_tokens_cache_write: null,
        reasoning_tokens: null,
        total_cost: null
      }
    },
    timestamp: ts(BASE, startSec).toISOString(),
    working_start: startSec,
    working_time: endSec - startSec,
    cache: null,
    call: null,
    completed: null,
    error: errorMsg,
    metadata: null,
    pending: null,
    retries: null,
    role: null,
    span_id: null,
    traceback: null,
    traceback_ansi: null,
    uuid: null
  };
  return {
    type: "event",
    event,
    startTime: ts(BASE, startSec),
    endTime: ts(BASE, endSec),
    totalTokens: tokens,
    idleTime: 0
  };
}
function makeCompactionEventNode(tokensBefore, tokensAfter, startSec, endSec) {
  const event = {
    event: "compaction",
    type: "summary",
    tokens_before: tokensBefore,
    tokens_after: tokensAfter,
    timestamp: ts(BASE, startSec).toISOString(),
    working_start: startSec,
    metadata: null,
    pending: null,
    source: null,
    span_id: null,
    uuid: null
  };
  return {
    type: "event",
    event,
    startTime: ts(BASE, startSec),
    endTime: ts(BASE, endSec),
    totalTokens: 0,
    idleTime: 0
  };
}
function makeSpan(id, name, spanType, startSec, endSec, tokens, content2 = [], options) {
  return {
    type: "span",
    id,
    name,
    spanType,
    content: content2,
    branches: options?.branches ?? [],
    description: options?.description,
    utility: options?.utility ?? false,
    startTime: ts(BASE, startSec),
    endTime: ts(BASE, endSec),
    totalTokens: tokens,
    idleTime: 0
  };
}
function makeTimeline(root, options) {
  if (options?.scoring) {
    const scoring = options.scoring;
    const newContent = [...root.content, scoring];
    const endTime = scoring.endTime > root.endTime ? scoring.endTime : root.endTime;
    return {
      name: "Default",
      description: "",
      root: {
        ...root,
        content: newContent,
        endTime,
        totalTokens: root.totalTokens + scoring.totalTokens,
        idleTime: 0
      }
    };
  }
  return { name: "Default", description: "", root };
}
function sequentialAgents() {
  const explore = makeSpan(
    "explore",
    "Explore",
    "agent",
    2,
    14,
    8100,
    [
      makeModelEventNode("Let me examine the project structure.", 2, 5, 2400),
      makeToolEventNode(
        "bash",
        { cmd: "find . -type f" },
        "src/\nlib/\ntests/",
        5,
        7,
        800
      ),
      makeModelEventNode(
        "I see a standard project layout. Let me look at the main module.",
        7,
        10,
        2600
      ),
      makeToolEventNode(
        "read_file",
        { path: "src/main.py" },
        "def main(): ...",
        10,
        12,
        1200
      ),
      makeModelEventNode("The main entry point is clear.", 12, 14, 1100)
    ],
    {
      description: "Explore the project structure and understand the codebase"
    }
  );
  const plan = makeSpan(
    "plan",
    "Plan",
    "agent",
    15,
    24,
    5300,
    [
      makeModelEventNode(
        "Based on my exploration, I'll plan the implementation.",
        15,
        18,
        1800
      ),
      makeToolEventNode(
        "bash",
        { cmd: "wc -l src/*.py" },
        "142 total",
        18,
        19,
        400
      ),
      makeModelEventNode(
        "The plan is: 1) Refactor core module, 2) Add tests, 3) Update docs.",
        19,
        24,
        3100
      )
    ],
    {
      description: "Create an implementation plan based on exploration findings"
    }
  );
  const build = makeSpan(
    "build",
    "Build",
    "agent",
    25,
    52,
    31800,
    [
      makeModelEventNode(
        "Starting implementation of the refactored module.",
        25,
        29,
        4200
      ),
      makeToolEventNode(
        "write_file",
        { path: "src/core.py" },
        "File written successfully",
        29,
        32,
        2800
      ),
      makeModelEventNode(
        "Core module done. Now adding test coverage.",
        32,
        36,
        3600
      ),
      makeToolEventNode(
        "write_file",
        { path: "tests/test_core.py" },
        "File written successfully",
        36,
        40,
        3200
      ),
      makeToolEventNode(
        "bash",
        { cmd: "pytest tests/" },
        "5 passed",
        40,
        44,
        1e3
      ),
      makeModelEventNode(
        "All tests pass. Updating documentation.",
        44,
        48,
        3400
      ),
      makeToolEventNode(
        "write_file",
        { path: "docs/api.md" },
        "File written successfully",
        48,
        50,
        2600
      ),
      makeModelEventNode(
        "Implementation complete with full test coverage.",
        50,
        52,
        11e3
      )
    ],
    {
      description: "Implement the refactored module with tests and documentation"
    }
  );
  const scoring = makeSpan("scoring", "Scoring", "scorers", 53, 58, 3200);
  const transcript = makeSpan(
    "transcript",
    "Transcript",
    "agent",
    0,
    58,
    48500,
    [
      makeModelEventNode(
        "I'll work through this task step by step.",
        0,
        2,
        1500
      ),
      explore,
      plan,
      build,
      makeModelEventNode("All phases complete. Task finished.", 52, 53, 700)
    ]
  );
  return {
    name: "Sequential agents",
    description: "S1 — Explore → Plan → Build → Scoring",
    timeline: makeTimeline(transcript, { scoring })
  };
}
function iterativeAgents() {
  const explore1 = makeSpan("explore-1", "Explore", "agent", 2, 10, 7200, [
    makeModelEventNode("Initial exploration of the codebase.", 2, 5, 2800),
    makeToolEventNode(
      "bash",
      { cmd: "ls -la src/" },
      "core.py\nutils.py\nconfig.py",
      5,
      6,
      600
    ),
    makeModelEventNode("Found key files. Checking dependencies.", 6, 9, 2400),
    makeToolEventNode(
      "bash",
      { cmd: "pip list" },
      "requests==2.31\nflask==3.0",
      9,
      10,
      1400
    )
  ]);
  const plan1 = makeSpan("plan-1", "Plan", "agent", 11, 18, 4600, [
    makeModelEventNode(
      "First iteration plan: focus on core module.",
      11,
      14,
      2200
    ),
    makeToolEventNode(
      "read_file",
      { path: "src/core.py" },
      "class Core: ...",
      14,
      16,
      1e3
    ),
    makeModelEventNode("Need more info before finalizing plan.", 16, 18, 1400)
  ]);
  const explore2 = makeSpan("explore-2", "Explore", "agent", 19, 26, 7300, [
    makeModelEventNode(
      "Second exploration pass: checking edge cases.",
      19,
      22,
      2600
    ),
    makeToolEventNode(
      "bash",
      { cmd: "grep -r 'TODO' src/" },
      "core.py:12: TODO fix",
      22,
      23,
      800
    ),
    makeModelEventNode("Found TODOs. Reviewing test coverage.", 23, 26, 3900)
  ]);
  const plan2 = makeSpan("plan-2", "Plan", "agent", 27, 33, 4600, [
    makeModelEventNode("Revised plan with edge case handling.", 27, 30, 2400),
    makeModelEventNode(
      "Plan finalized: address TODOs and add error handling.",
      30,
      33,
      2200
    )
  ]);
  const build = makeSpan("build", "Build", "agent", 34, 55, 34600, [
    makeModelEventNode("Implementing planned changes.", 34, 38, 5200),
    makeToolEventNode(
      "write_file",
      { path: "src/core.py" },
      "File written",
      38,
      42,
      4800
    ),
    makeToolEventNode(
      "write_file",
      { path: "src/utils.py" },
      "File written",
      42,
      45,
      3600
    ),
    makeModelEventNode("Running tests to verify changes.", 45, 48, 3200),
    makeToolEventNode(
      "bash",
      { cmd: "pytest -v" },
      "8 passed, 0 failed",
      48,
      51,
      1200
    ),
    makeModelEventNode("All tests pass. Build complete.", 51, 55, 16600)
  ]);
  const scoring = makeSpan("scoring", "Scoring", "scorers", 56, 60, 3200);
  const transcript = makeSpan(
    "transcript",
    "Transcript",
    "agent",
    0,
    60,
    61500,
    [explore1, plan1, explore2, plan2, build]
  );
  return {
    name: "Iterative agents",
    description: "S2 — Explore and Plan with multiple spans",
    timeline: makeTimeline(transcript, { scoring })
  };
}
function deepNesting() {
  const generate = makeSpan("generate", "Generate", "agent", 46, 58, 5800, [
    makeModelEventNode("Generating test cases for the module.", 46, 50, 2400),
    makeToolEventNode(
      "write_file",
      { path: "tests/test_gen.py" },
      "File written",
      50,
      54,
      1800
    ),
    makeModelEventNode("Test cases generated successfully.", 54, 58, 1600)
  ]);
  const run = makeSpan("run", "Run", "agent", 59, 64, 400, [
    makeToolEventNode(
      "bash",
      { cmd: "pytest tests/test_gen.py" },
      "Running...",
      59,
      61,
      200
    ),
    makeToolErrorEventNode(
      "bash",
      "Process timed out after 30s",
      "timeout",
      61,
      64,
      200
    )
  ]);
  const evaluate = makeSpan("evaluate", "Evaluate", "agent", 65, 75, 4200, [
    makeModelEventNode(
      "Evaluating test results despite timeout.",
      65,
      69,
      1800
    ),
    makeToolEventNode(
      "read_file",
      { path: "tests/test_gen.py" },
      "def test_basic(): ...",
      69,
      71,
      600
    ),
    makeModelEventNode(
      "Test needs adjustment for timeout. Evaluation complete.",
      71,
      75,
      1800
    )
  ]);
  const code = makeSpan("code", "Code", "agent", 22, 44, 15200, [
    makeModelEventNode("Writing the core implementation.", 22, 26, 3200),
    makeToolEventNode(
      "write_file",
      { path: "src/module.py" },
      "File written",
      26,
      30,
      2800
    ),
    makeCompactionEventNode(12e3, 6500, 30, 31),
    makeModelEventNode("Continuing after context compaction.", 31, 36, 4400),
    makeToolEventNode(
      "write_file",
      { path: "src/helpers.py" },
      "File written",
      36,
      40,
      2400
    ),
    makeModelEventNode("Code implementation phase complete.", 40, 44, 2400)
  ]);
  const test = makeSpan("test", "Test", "agent", 45, 75, 10400, [
    makeModelEventNode("Setting up test infrastructure.", 45, 46, 600),
    generate,
    run,
    evaluate
  ]);
  const fix = makeSpan("fix", "Fix", "agent", 76, 88, 6200, [
    makeModelEventNode("Fixing the timeout issue in tests.", 76, 80, 2200),
    makeToolEventNode(
      "write_file",
      { path: "tests/test_gen.py" },
      "File updated",
      80,
      83,
      1800
    ),
    makeToolEventNode(
      "bash",
      { cmd: "pytest tests/" },
      "3 passed",
      83,
      86,
      800
    ),
    makeModelEventNode("All tests pass after fixes.", 86, 88, 1400)
  ]);
  const explore = makeSpan("explore", "Explore", "agent", 2, 18, 6400, [
    makeModelEventNode("Examining the project structure.", 2, 6, 2200),
    makeToolEventNode(
      "bash",
      { cmd: "find . -type f" },
      "src/\nlib/\ntests/",
      6,
      9,
      800
    ),
    makeModelEventNode("Project structure understood.", 9, 14, 2e3),
    makeToolEventNode(
      "read_file",
      { path: "src/main.py" },
      "def main(): ...",
      14,
      18,
      1400
    )
  ]);
  const build = makeSpan("build", "Build", "agent", 20, 88, 31800, [
    makeModelEventNode("Starting the build process.", 20, 22, 800),
    code,
    test,
    fix
  ]);
  const scoring = makeSpan("scoring", "Scoring", "scorers", 90, 95, 3200);
  const transcript = makeSpan(
    "transcript",
    "Transcript",
    "agent",
    0,
    95,
    41400,
    [explore, build]
  );
  return {
    name: "Deep nesting (3 levels)",
    description: "S3 — Explore → Build → Code/Test/Fix, Test → Generate/Run/Evaluate",
    timeline: makeTimeline(transcript, { scoring })
  };
}
function parallelAgents() {
  const explore1 = makeSpan(
    "explore-1",
    "Explore",
    "agent",
    2,
    14,
    8100,
    [
      makeModelEventNode("Exploring API documentation.", 2, 5, 2800),
      makeToolEventNode(
        "bash",
        { cmd: "curl api/docs" },
        '{"endpoints": [...]}',
        5,
        8,
        1400
      ),
      makeModelEventNode("API structure documented.", 8, 11, 2200),
      makeToolEventNode(
        "read_file",
        { path: "api/schema.json" },
        '{"type": "object"}',
        11,
        14,
        1700
      )
    ],
    { description: "Search for API documentation" }
  );
  const explore2 = makeSpan(
    "explore-2",
    "Explore",
    "agent",
    3,
    16,
    9400,
    [
      makeModelEventNode("Exploring database schema.", 3, 7, 3200),
      makeToolEventNode(
        "bash",
        { cmd: "sqlite3 db.sqlite .schema" },
        "CREATE TABLE users ...",
        7,
        10,
        1600
      ),
      makeModelEventNode("Database schema analyzed.", 10, 13, 2800),
      makeToolEventNode(
        "bash",
        { cmd: "sqlite3 db.sqlite 'SELECT count(*) FROM users'" },
        "1247",
        13,
        16,
        1800
      )
    ],
    { description: "Analyze existing database schema and data" }
  );
  const explore3 = makeSpan(
    "explore-3",
    "Explore",
    "agent",
    2,
    12,
    6800,
    [
      makeModelEventNode("Exploring frontend components.", 2, 5, 2400),
      makeToolEventNode(
        "bash",
        { cmd: "ls src/components/" },
        "Header.tsx\nFooter.tsx",
        5,
        7,
        800
      ),
      makeModelEventNode("Frontend component inventory complete.", 7, 10, 2200),
      makeToolEventNode(
        "read_file",
        { path: "src/App.tsx" },
        "function App() { ... }",
        10,
        12,
        1400
      )
    ],
    { description: "Inventory frontend components and architecture" }
  );
  const plan = makeSpan("plan", "Plan", "agent", 17, 25, 5300, [
    makeModelEventNode(
      "Synthesizing findings from all exploration tracks.",
      17,
      20,
      2400
    ),
    makeModelEventNode("Implementation plan ready.", 20, 25, 2900)
  ]);
  const build = makeSpan("build", "Build", "agent", 26, 52, 27600, [
    makeModelEventNode("Starting full-stack implementation.", 26, 30, 4200),
    makeToolEventNode(
      "write_file",
      { path: "src/api/routes.py" },
      "File written",
      30,
      34,
      3800
    ),
    makeToolEventNode(
      "write_file",
      { path: "src/components/Dashboard.tsx" },
      "File written",
      34,
      38,
      4200
    ),
    makeModelEventNode(
      "Core components built. Adding integration.",
      38,
      42,
      3600
    ),
    makeToolEventNode(
      "bash",
      { cmd: "npm run build" },
      "Build successful",
      42,
      46,
      1200
    ),
    makeModelEventNode("Build and integration complete.", 46, 52, 10600)
  ]);
  const scoring = makeSpan("scoring", "Scoring", "scorers", 53, 57, 3200);
  const transcript = makeSpan(
    "transcript",
    "Transcript",
    "agent",
    0,
    57,
    60400,
    [explore1, explore2, explore3, plan, build]
  );
  return {
    name: "Parallel agents",
    description: "S4 — Explore (3) parallel group + Plan + Build",
    timeline: makeTimeline(transcript, { scoring })
  };
}
function inlineMarkers() {
  const agent = makeSpan("agent", "Agent", "agent", 2, 55, 42e3, [
    makeModelEventNode("Starting work on the task.", 2, 6, 3200),
    makeToolEventNode(
      "bash",
      { cmd: "npm install" },
      "added 142 packages",
      6,
      10,
      1200
    ),
    makeModelEventNode("Dependencies installed. Writing code.", 10, 16, 4800),
    makeToolEventNode(
      "write_file",
      { path: "src/feature.ts" },
      "File written",
      16,
      20,
      3600
    ),
    makeModelErrorEventNode(
      "Attempting to call the API",
      "Rate limit exceeded: 429 Too Many Requests",
      20,
      24,
      2400
    ),
    makeModelEventNode(
      "Retrying after rate limit. Adjusting approach.",
      24,
      28,
      3200
    ),
    makeToolEventNode(
      "bash",
      { cmd: "curl -X POST api/endpoint" },
      '{"status": "ok"}',
      28,
      31,
      1400
    ),
    makeToolErrorEventNode(
      "bash",
      "Command timed out after 60s",
      "timeout",
      31,
      35,
      800
    ),
    makeModelEventNode(
      "Tool timed out. Working around the issue.",
      35,
      39,
      3800
    ),
    makeCompactionEventNode(15e3, 8e3, 39, 40),
    makeModelEventNode(
      "Context compacted. Continuing with reduced history.",
      40,
      45,
      5200
    ),
    makeToolEventNode(
      "write_file",
      { path: "src/feature.ts" },
      "File updated",
      45,
      49,
      4800
    ),
    makeModelEventNode("Feature implementation complete.", 49, 55, 7600)
  ]);
  const scoring = makeSpan("scoring", "Scoring", "scorers", 56, 60, 3200);
  const transcript = makeSpan(
    "transcript",
    "Transcript",
    "agent",
    0,
    60,
    45200,
    [agent]
  );
  return {
    name: "Inline markers",
    description: "S5 — Agent with error and compaction events",
    timeline: makeTimeline(transcript, { scoring })
  };
}
function flatTranscript() {
  const transcript = makeSpan(
    "transcript",
    "Transcript",
    "agent",
    0,
    40,
    12400,
    [
      makeModelEventNode("Analyzing the user request.", 0, 4, 1800),
      makeToolEventNode(
        "bash",
        { cmd: "ls -la" },
        "total 42\ndrwxr-xr-x ...",
        4,
        6,
        600
      ),
      makeModelEventNode(
        "I see the project files. Let me read the config.",
        6,
        10,
        2200
      ),
      makeToolEventNode(
        "read_file",
        { path: "config.yaml" },
        "port: 8080\ndb: postgres",
        10,
        12,
        800
      ),
      makeModelEventNode(
        "Configuration loaded. Making the requested change.",
        12,
        18,
        2400
      ),
      makeToolEventNode(
        "write_file",
        { path: "config.yaml" },
        "port: 9090\ndb: postgres",
        18,
        20,
        600
      ),
      makeToolEventNode(
        "bash",
        { cmd: "python validate.py" },
        "Config valid",
        20,
        23,
        400
      ),
      makeModelEventNode(
        "Change applied and validated successfully.",
        23,
        28,
        1800
      ),
      makeToolEventNode(
        "bash",
        { cmd: "python -m pytest" },
        "12 passed",
        28,
        34,
        800
      ),
      makeModelEventNode("All tests pass. Task complete.", 34, 40, 900)
    ]
  );
  return {
    name: "Flat transcript",
    description: "S7 — Single agent, no children, just events",
    timeline: makeTimeline(transcript)
  };
}
function manyRows() {
  const names = [
    "Research",
    "Analyze",
    "Design",
    "Implement",
    "Test",
    "Review",
    "Refactor",
    "Deploy",
    "Monitor",
    "Cleanup"
  ];
  const agentEvents = [
    // Research
    [["bash", { cmd: "search docs" }, "Found 5 relevant docs"]],
    // Analyze
    [["read_file", { path: "src/main.py" }, "class Main: ..."]],
    // Design
    [["write_file", { path: "design.md" }, "Written"]],
    // Implement
    [["write_file", { path: "src/feature.py" }, "Written"]],
    // Test — model error agent
    [["bash", { cmd: "pytest" }, "3 passed, 1 failed"]],
    // Review
    [["bash", { cmd: "ruff check src/" }, "All checks passed"]],
    // Refactor — compaction agent
    [["write_file", { path: "src/refactored.py" }, "Written"]],
    // Deploy
    [["bash", { cmd: "docker build ." }, "Successfully built abc123"]],
    // Monitor
    [["bash", { cmd: "curl health" }, '{"status":"healthy"}']],
    // Cleanup
    [["bash", { cmd: "rm -rf tmp/" }, "Cleaned"]]
  ];
  const agents = [];
  let offset = 2;
  let totalTokens = 0;
  for (let i = 0; i < names.length; i++) {
    const duration = 4 + Math.floor(i * 0.5);
    const tokens = 2e3 + i * 1100;
    const name = names[i] ?? `Agent ${i}`;
    const evts = agentEvents[i] ?? [];
    const mid = offset + Math.floor(duration / 2);
    const content2 = [
      makeModelEventNode(
        `Starting ${name.toLowerCase()} phase.`,
        offset,
        mid,
        Math.floor(tokens * 0.4)
      )
    ];
    for (const [fn, args, result] of evts) {
      content2.push(
        makeToolEventNode(
          fn,
          args,
          result,
          mid,
          mid + 1,
          Math.floor(tokens * 0.2)
        )
      );
    }
    if (i === 4) {
      content2.push(
        makeModelErrorEventNode(
          "Attempting test analysis",
          "Context length exceeded",
          mid + 1,
          mid + 2,
          Math.floor(tokens * 0.1)
        )
      );
    }
    if (i === 6) {
      content2.push(makeCompactionEventNode(9e3, 5e3, mid + 1, mid + 2));
    }
    content2.push(
      makeModelEventNode(
        `${name} phase complete.`,
        offset + duration - 1,
        offset + duration,
        Math.floor(tokens * 0.3)
      )
    );
    agents.push(
      makeSpan(
        `agent-${i}`,
        name,
        "agent",
        offset,
        offset + duration,
        tokens,
        content2
      )
    );
    totalTokens += tokens;
    offset += duration + 1;
  }
  const transcript = makeSpan(
    "transcript",
    "Transcript",
    "agent",
    0,
    offset,
    totalTokens,
    agents
  );
  return {
    name: "Many rows (8+)",
    description: "S8 — Tests 6-row cap / scrolling with 10 agents",
    timeline: makeTimeline(transcript)
  };
}
function utilityAgents() {
  const util1 = makeSpan(
    "util-1",
    "bash_checker",
    "agent",
    3,
    4,
    300,
    [
      makeToolEventNode(
        "bash",
        { cmd: "shellcheck script.sh" },
        "No issues",
        3,
        4,
        300
      )
    ],
    {
      utility: true
    }
  );
  const util2 = makeSpan(
    "util-2",
    "safety_validator",
    "agent",
    8,
    9,
    200,
    [makeToolEventNode("validate", { rule: "safety" }, "Pass", 8, 9, 200)],
    {
      utility: true
    }
  );
  const util3 = makeSpan(
    "util-3",
    "bash_checker",
    "agent",
    14,
    15,
    300,
    [
      makeToolEventNode(
        "bash",
        { cmd: "shellcheck deploy.sh" },
        "No issues",
        14,
        15,
        300
      )
    ],
    {
      utility: true
    }
  );
  const util4 = makeSpan(
    "util-4",
    "format_checker",
    "agent",
    20,
    21,
    250,
    [
      makeToolEventNode(
        "format",
        { target: "src/" },
        "All files formatted",
        20,
        21,
        250
      )
    ],
    {
      utility: true
    }
  );
  const mainAgent = makeSpan("main", "Build", "agent", 2, 45, 28e3, [
    makeModelEventNode("Starting build with safety checks.", 2, 3, 1200),
    util1,
    makeModelEventNode(
      "Bash check passed. Writing implementation.",
      4,
      8,
      3800
    ),
    util2,
    makeToolEventNode(
      "write_file",
      { path: "src/build.py" },
      "Written",
      9,
      13,
      4200
    ),
    makeModelEventNode(
      "Core written. Continuing with more code.",
      13,
      14,
      2400
    ),
    util3,
    makeToolEventNode(
      "write_file",
      { path: "src/deploy.py" },
      "Written",
      15,
      19,
      3600
    ),
    makeModelEventNode(
      "Deploy script ready. Running format check.",
      19,
      20,
      2200
    ),
    util4,
    makeModelEventNode("All checks passed. Build complete.", 21, 30, 4800),
    makeToolEventNode(
      "bash",
      { cmd: "python -m build" },
      "Build successful",
      30,
      40,
      2400
    ),
    makeModelEventNode("Package built and ready.", 40, 45, 3400)
  ]);
  const transcript = makeSpan(
    "transcript",
    "Transcript",
    "agent",
    0,
    50,
    29050,
    [mainAgent]
  );
  return {
    name: "Utility agents",
    description: "S10 — Agent with multiple utility children",
    timeline: makeTimeline(transcript)
  };
}
function branchesSingleFork() {
  const branch1Refactor = makeSpan(
    "branch1-refactor",
    "Refactor",
    "agent",
    15,
    22,
    5200,
    [
      makeModelEventNode("Refactoring the module for clarity.", 15, 18, 2400),
      makeToolEventNode(
        "write_file",
        { path: "src/refactored.py" },
        "Written",
        18,
        20,
        1600
      ),
      makeModelEventNode("Refactoring complete.", 20, 22, 1200)
    ]
  );
  const branch1Validate = makeSpan(
    "branch1-validate",
    "Validate",
    "agent",
    23,
    28,
    3500,
    [
      makeModelEventNode("Validating the refactored code.", 23, 25, 1400),
      makeToolEventNode(
        "bash",
        { cmd: "pytest tests/" },
        "6 passed",
        25,
        27,
        800
      ),
      makeModelEventNode("Validation passed.", 27, 28, 1300)
    ]
  );
  const branch1 = {
    type: "branch",
    forkedAt: "model-call-5",
    content: [branch1Refactor, branch1Validate],
    startTime: ts(BASE, 15),
    endTime: ts(BASE, 28),
    totalTokens: 8700,
    idleTime: 0
  };
  const branch2Rewrite = makeSpan(
    "branch2-rewrite",
    "Rewrite",
    "agent",
    15,
    25,
    5100,
    [
      makeModelEventNode(
        "Taking a different approach: full rewrite.",
        15,
        19,
        2200
      ),
      makeToolEventNode(
        "write_file",
        { path: "src/rewritten.py" },
        "Written",
        19,
        22,
        1800
      ),
      makeModelEventNode("Rewrite approach complete.", 22, 25, 1100)
    ]
  );
  const branch2 = {
    type: "branch",
    forkedAt: "model-call-5",
    content: [branch2Rewrite],
    startTime: ts(BASE, 15),
    endTime: ts(BASE, 25),
    totalTokens: 5100,
    idleTime: 0
  };
  const code = makeSpan("code", "Code", "agent", 2, 24, 15200, [
    makeModelEventNode("Writing initial implementation.", 2, 6, 4200),
    makeToolEventNode(
      "write_file",
      { path: "src/module.py" },
      "Written",
      6,
      10,
      3200
    ),
    makeModelEventNode(
      "Initial code written. Iterating on design.",
      10,
      16,
      4400
    ),
    makeToolEventNode(
      "write_file",
      { path: "src/module.py" },
      "Updated",
      16,
      20,
      2e3
    ),
    makeModelEventNode("Code phase finalized.", 20, 24, 1400)
  ]);
  const test = makeSpan("test", "Test", "agent", 25, 40, 10400, [
    makeModelEventNode("Setting up test suite.", 25, 28, 2200),
    makeToolEventNode(
      "write_file",
      { path: "tests/test_module.py" },
      "Written",
      28,
      32,
      3400
    ),
    makeToolEventNode(
      "bash",
      { cmd: "pytest tests/" },
      "7 passed",
      32,
      36,
      1200
    ),
    makeModelEventNode("All tests passing.", 36, 40, 3600)
  ]);
  const build = makeSpan(
    "build",
    "Build",
    "agent",
    1,
    52,
    31800,
    [
      makeModelEventNode(
        "Starting build with branching strategy.",
        1,
        2,
        800,
        "model-call-5"
      ),
      code,
      test,
      makeModelEventNode("Build complete. Best branch selected.", 40, 52, 5400)
    ],
    {
      branches: [branch1, branch2]
    }
  );
  const transcript = makeSpan(
    "transcript",
    "Transcript",
    "agent",
    0,
    55,
    31800,
    [build]
  );
  return {
    name: "Branches (single fork)",
    description: "S11 — Agent with 2 branches at one fork point",
    timeline: makeTimeline(transcript)
  };
}
function branchesMultipleForks() {
  const earlyAttempt = makeSpan(
    "early-attempt",
    "Attempt",
    "agent",
    8,
    14,
    4200,
    [
      makeModelEventNode("Early attempt at solving the problem.", 8, 11, 2e3),
      makeToolEventNode(
        "bash",
        { cmd: "python solve.py" },
        "Partial result",
        11,
        13,
        1200
      ),
      makeModelEventNode("Attempt did not fully succeed.", 13, 14, 1e3)
    ]
  );
  const earlyBranch = {
    type: "branch",
    forkedAt: "model-call-3",
    content: [earlyAttempt],
    startTime: ts(BASE, 8),
    endTime: ts(BASE, 14),
    totalTokens: 4200,
    idleTime: 0
  };
  const lateRetry = makeSpan("late-retry", "Retry", "agent", 30, 38, 3800, [
    makeModelEventNode("Retrying with modified parameters.", 30, 33, 1600),
    makeToolEventNode(
      "bash",
      { cmd: "python solve.py --retry" },
      "Better result",
      33,
      36,
      1e3
    ),
    makeModelEventNode("Retry showed improvement.", 36, 38, 1200)
  ]);
  const lateBranch1 = {
    type: "branch",
    forkedAt: "model-call-10",
    content: [lateRetry],
    startTime: ts(BASE, 30),
    endTime: ts(BASE, 38),
    totalTokens: 3800,
    idleTime: 0
  };
  const lateAlt = makeSpan("late-alt", "Alternative", "agent", 30, 42, 6100, [
    makeModelEventNode(
      "Trying a completely different algorithm.",
      30,
      34,
      2400
    ),
    makeToolEventNode(
      "write_file",
      { path: "src/alt_solver.py" },
      "Written",
      34,
      37,
      1800
    ),
    makeToolEventNode(
      "bash",
      { cmd: "python alt_solver.py" },
      "Success!",
      37,
      40,
      800
    ),
    makeModelEventNode("Alternative approach succeeded.", 40, 42, 1100)
  ]);
  const lateBranch2 = {
    type: "branch",
    forkedAt: "model-call-10",
    content: [lateAlt],
    startTime: ts(BASE, 30),
    endTime: ts(BASE, 42),
    totalTokens: 6100,
    idleTime: 0
  };
  const code = makeSpan("code", "Code", "agent", 2, 28, 15200, [
    makeModelEventNode("Beginning code implementation.", 2, 6, 3600),
    makeToolEventNode(
      "write_file",
      { path: "src/solver.py" },
      "Written",
      6,
      10,
      2800
    ),
    makeModelEventNode("Core solver implemented.", 10, 16, 4200),
    makeToolEventNode(
      "bash",
      { cmd: "python solver.py" },
      "Initial results",
      16,
      20,
      1400
    ),
    makeModelEventNode("Optimizing the solver.", 20, 28, 3200)
  ]);
  const test = makeSpan("test", "Test", "agent", 29, 48, 10400, [
    makeModelEventNode("Running comprehensive test suite.", 29, 33, 2800),
    makeToolEventNode(
      "bash",
      { cmd: "pytest tests/ -v" },
      "12 passed",
      33,
      38,
      1600
    ),
    makeModelEventNode("Tests validated. Checking edge cases.", 38, 43, 3200),
    makeToolEventNode(
      "bash",
      { cmd: "pytest tests/edge_cases.py" },
      "4 passed",
      43,
      46,
      1e3
    ),
    makeModelEventNode("All edge cases handled.", 46, 48, 1800)
  ]);
  const build = makeSpan(
    "build",
    "Build",
    "agent",
    1,
    55,
    31800,
    [
      makeModelEventNode(
        "Starting build with exploration branches.",
        1,
        2,
        600,
        "model-call-3"
      ),
      code,
      makeModelEventNode(
        "Evaluating approaches.",
        28,
        29,
        400,
        "model-call-10"
      ),
      test,
      makeModelEventNode(
        "Build finalized after exploring alternatives.",
        48,
        55,
        5800
      )
    ],
    {
      branches: [earlyBranch, lateBranch1, lateBranch2]
    }
  );
  const transcript = makeSpan(
    "transcript",
    "Transcript",
    "agent",
    0,
    58,
    31800,
    [build]
  );
  return {
    name: "Branches (multiple forks)",
    description: "S11 — Agent with branches at different fork points",
    timeline: makeTimeline(transcript)
  };
}
const timelineScenarios = [
  sequentialAgents(),
  iterativeAgents(),
  deepNesting(),
  parallelAgents(),
  inlineMarkers(),
  flatTranscript(),
  manyRows(),
  utilityAgents(),
  branchesSingleFork(),
  branchesMultipleForks()
];
const container = "_container_1w6el_1";
const headerRow = "_headerRow_1w6el_8";
const title = "_title_1w6el_17";
const scenarioSelect = "_scenarioSelect_1w6el_25";
const markerDepthSelect = "_markerDepthSelect_1w6el_29";
const scenarioDescription = "_scenarioDescription_1w6el_33";
const content = "_content_1w6el_38";
const eventsContainer = "_eventsContainer_1w6el_45";
const outlineCollapsed = "_outlineCollapsed_1w6el_53";
const outlinePane = "_outlinePane_1w6el_57";
const outline = "_outline_1w6el_53";
const outlineToggle = "_outlineToggle_1w6el_70";
const eventsSeparator = "_eventsSeparator_1w6el_78";
const eventList = "_eventList_1w6el_82";
const emptyEvents = "_emptyEvents_1w6el_86";
const styles = {
  container,
  headerRow,
  title,
  scenarioSelect,
  markerDepthSelect,
  scenarioDescription,
  content,
  eventsContainer,
  outlineCollapsed,
  outlinePane,
  outline,
  outlineToggle,
  eventsSeparator,
  eventList,
  emptyEvents
};
const TimelinePanel = () => {
  useDocumentTitle("Timeline");
  const [selectedIndex, setSelectedIndex] = reactExports.useState(0);
  const [markerDepth, setMarkerDepth] = reactExports.useState("direct");
  const [outlineCollapsed2, setOutlineCollapsed] = useProperty(
    "timeline",
    "outlineCollapsed",
    { defaultValue: true, cleanup: false }
  );
  const isOutlineCollapsed = !!outlineCollapsed2;
  const scenario = timelineScenarios[selectedIndex];
  const timeline = scenario?.timeline ?? timelineScenarios[0].timeline;
  const state = useTimeline(timeline);
  reactExports.useEffect(() => {
    state.navigateTo("");
  }, []);
  const timeMapping = reactExports.useMemo(
    () => computeTimeMapping(state.node),
    [state.node]
  );
  const rootTimeMapping = reactExports.useMemo(
    () => computeTimeMapping(timeline.root),
    [timeline.root]
  );
  const layouts = reactExports.useMemo(
    () => computeRowLayouts(state.rows, timeMapping, markerDepth),
    [state.rows, timeMapping, markerDepth]
  );
  const atRoot = state.breadcrumbs.length <= 1;
  const selectedSpans = reactExports.useMemo(
    () => getSelectedSpans(state.rows, state.selected),
    [state.rows, state.selected]
  );
  const minimapSelection = reactExports.useMemo(
    () => computeMinimapSelection(state.rows, state.selected),
    [state.rows, state.selected]
  );
  const rawEvents = reactExports.useMemo(
    () => collectRawEvents(selectedSpans),
    [selectedSpans]
  );
  const { eventNodes, defaultCollapsedIds } = useEventNodes(rawEvents, false);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.container, children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.headerRow, children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: styles.title, children: "Timeline" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        VscodeSingleSelect,
        {
          value: String(selectedIndex),
          onChange: (e) => {
            const target = e.target;
            setSelectedIndex(Number(target.value));
            state.navigateTo("");
          },
          className: styles.scenarioSelect,
          children: timelineScenarios.map((s, i) => /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeOption, { value: String(i), children: s.name }, i))
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        VscodeSingleSelect,
        {
          value: markerDepth,
          onChange: (e) => {
            const target = e.target;
            setMarkerDepth(target.value);
          },
          className: styles.markerDepthSelect,
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeOption, { value: "direct", children: "Markers: direct" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeOption, { value: "children", children: "Markers: children" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeOption, { value: "recursive", children: "Markers: recursive" })
          ]
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: styles.scenarioDescription, children: scenario?.description })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.content, children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(TimelinePills, { timelines: [], activeIndex: 0, onSelect: () => {
      } }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        TimelineSwimLanes,
        {
          layouts,
          selected: state.selected,
          node: state.node,
          onSelect: state.select,
          onDrillDown: state.drillDown,
          onGoUp: state.goUp,
          minimap: {
            root: timeline.root,
            selection: minimapSelection,
            mapping: rootTimeMapping
          },
          breadcrumb: {
            breadcrumbs: state.breadcrumbs,
            atRoot,
            onGoUp: state.goUp,
            onNavigate: state.navigateTo,
            selected: state.selected
          }
        }
      ),
      eventNodes.length > 0 ? /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "div",
        {
          className: clsx(
            styles.eventsContainer,
            isOutlineCollapsed && styles.outlineCollapsed
          ),
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.outlinePane, children: [
              !isOutlineCollapsed && /* @__PURE__ */ jsxRuntimeExports.jsx(
                TranscriptOutline,
                {
                  eventNodes,
                  defaultCollapsedIds,
                  className: styles.outline
                }
              ),
              /* @__PURE__ */ jsxRuntimeExports.jsx(
                "div",
                {
                  className: styles.outlineToggle,
                  onClick: () => setOutlineCollapsed(!isOutlineCollapsed),
                  children: /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: ApplicationIcons.sidebar })
                }
              )
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.eventsSeparator }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.eventList, children: /* @__PURE__ */ jsxRuntimeExports.jsx(
              TranscriptViewNodes,
              {
                id: "timeline-events",
                eventNodes,
                defaultCollapsedIds
              }
            ) })
          ]
        }
      ) : /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.emptyEvents, children: "Select a swimlane row to view events" })
    ] })
  ] });
};
export {
  TimelinePanel
};
//# sourceMappingURL=TimelinePanel.js.map
