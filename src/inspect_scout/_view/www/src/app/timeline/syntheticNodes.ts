import type {
  AgentNodeType,
  BranchType,
  SectionNodeType,
  TranscriptNodes,
} from "../../components/transcript/nodes";

export interface TimelineScenario {
  name: string;
  description: string;
  nodes: TranscriptNodes;
}

/** Create a Date offset from a base time by the given number of seconds. */
function ts(baseMs: number, offsetSeconds: number): Date {
  return new Date(baseMs + offsetSeconds * 1000);
}

const BASE = new Date("2025-01-15T10:00:00Z").getTime();

// ---------------------------------------------------------------------------
// Helper factories
// ---------------------------------------------------------------------------

function makeAgent(
  id: string,
  name: string,
  startSec: number,
  endSec: number,
  tokens: number,
  content: AgentNodeType["content"] = [],
  options?: {
    branches?: BranchType[];
    utility?: boolean;
  }
): AgentNodeType {
  return {
    type: "agent",
    id,
    name,
    source: { source: "span", spanId: id },
    content,
    branches: options?.branches ?? [],
    utility: options?.utility ?? false,
    startTime: ts(BASE, startSec),
    endTime: ts(BASE, endSec),
    totalTokens: tokens,
  };
}

function makeSection(
  section: "init" | "scoring",
  startSec: number,
  endSec: number,
  tokens: number
): SectionNodeType {
  return {
    type: "section",
    section,
    content: [],
    startTime: ts(BASE, startSec),
    endTime: ts(BASE, endSec),
    totalTokens: tokens,
  };
}

function makeNodes(
  agent: AgentNodeType,
  options?: {
    init?: SectionNodeType;
    scoring?: SectionNodeType;
  }
): TranscriptNodes {
  const init = options?.init ?? null;
  const scoring = options?.scoring ?? null;
  const startTime = init?.startTime ?? agent.startTime;
  const endTime = scoring?.endTime ?? agent.endTime;
  const totalTokens =
    (init?.totalTokens ?? 0) + agent.totalTokens + (scoring?.totalTokens ?? 0);
  return { init, agent, scoring, startTime, endTime, totalTokens };
}

// ---------------------------------------------------------------------------
// Scenarios
// ---------------------------------------------------------------------------

// S1: Sequential agents
function sequentialAgents(): TimelineScenario {
  const explore = makeAgent("explore", "Explore", 2, 14, 8100);
  const plan = makeAgent("plan", "Plan", 15, 24, 5300);
  const build = makeAgent("build", "Build", 25, 52, 31800);
  const scoring = makeSection("scoring", 53, 58, 3200);

  const transcript = makeAgent("transcript", "Transcript", 0, 58, 48500, [
    explore,
    plan,
    build,
  ]);

  return {
    name: "Sequential agents",
    description: "S1 — Explore → Plan → Build → Scoring",
    nodes: makeNodes(transcript, { scoring }),
  };
}

// S2: Iterative agents (multiple spans for same agent name)
function iterativeAgents(): TimelineScenario {
  const explore1 = makeAgent("explore-1", "Explore", 2, 10, 7200);
  const plan1 = makeAgent("plan-1", "Plan", 11, 18, 4600);
  const explore2 = makeAgent("explore-2", "Explore", 19, 26, 7300);
  const plan2 = makeAgent("plan-2", "Plan", 27, 33, 4600);
  const build = makeAgent("build", "Build", 34, 55, 34600);
  const scoring = makeSection("scoring", 56, 60, 3200);

  const transcript = makeAgent("transcript", "Transcript", 0, 60, 61500, [
    explore1,
    plan1,
    explore2,
    plan2,
    build,
  ]);

  return {
    name: "Iterative agents",
    description: "S2 — Explore and Plan with multiple spans",
    nodes: makeNodes(transcript, { scoring }),
  };
}

// S3: Deep nesting (3 levels)
function deepNesting(): TimelineScenario {
  const generate = makeAgent("generate", "Generate", 26, 38, 5800);
  const run = makeAgent("run", "Run", 39, 44, 400);
  const evaluate = makeAgent("evaluate", "Evaluate", 45, 55, 4200);

  const code = makeAgent("code", "Code", 2, 24, 15200);
  const test = makeAgent("test", "Test", 25, 55, 10400, [
    generate,
    run,
    evaluate,
  ]);
  const fix = makeAgent("fix", "Fix", 56, 68, 6200);

  const build = makeAgent("build", "Build", 1, 68, 31800, [code, test, fix]);
  const scoring = makeSection("scoring", 69, 72, 3200);

  const transcript = makeAgent("transcript", "Transcript", 0, 72, 35000, [
    build,
  ]);

  return {
    name: "Deep nesting (3 levels)",
    description: "S3 — Build → Code/Test/Fix, Test → Generate/Run/Evaluate",
    nodes: makeNodes(transcript, { scoring }),
  };
}

// S4: Parallel agents
function parallelAgents(): TimelineScenario {
  const explore1 = makeAgent("explore-1", "Explore", 2, 14, 8100);
  const explore2 = makeAgent("explore-2", "Explore", 3, 16, 9400);
  const explore3 = makeAgent("explore-3", "Explore", 2, 12, 6800);
  const plan = makeAgent("plan", "Plan", 17, 25, 5300);
  const build = makeAgent("build", "Build", 26, 52, 27600);
  const scoring = makeSection("scoring", 53, 57, 3200);

  const transcript = makeAgent("transcript", "Transcript", 0, 57, 60400, [
    explore1,
    explore2,
    explore3,
    plan,
    build,
  ]);

  return {
    name: "Parallel agents",
    description: "S4 — Explore (3) parallel group + Plan + Build",
    nodes: makeNodes(transcript, { scoring }),
  };
}

// S5: Inline markers (error and compaction events)
function inlineMarkers(): TimelineScenario {
  const agent = makeAgent("agent", "Agent", 2, 55, 42000);
  const scoring = makeSection("scoring", 56, 60, 3200);

  const transcript = makeAgent("transcript", "Transcript", 0, 60, 45200, [
    agent,
  ]);

  return {
    name: "Inline markers",
    description: "S5 — Agent with error and compaction events",
    nodes: makeNodes(transcript, { scoring }),
  };
}

// S7: Flat transcript (single agent, no children)
function flatTranscript(): TimelineScenario {
  const transcript = makeAgent("transcript", "Transcript", 0, 40, 12400);

  return {
    name: "Flat transcript",
    description: "S7 — Single agent, no children, just events",
    nodes: makeNodes(transcript),
  };
}

// S8: Many rows (8+ agents to test scrolling)
function manyRows(): TimelineScenario {
  const agents: AgentNodeType[] = [];
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
    "Cleanup",
  ];
  let offset = 2;
  let totalTokens = 0;
  for (let i = 0; i < names.length; i++) {
    const duration = 4 + Math.floor(i * 0.5);
    const tokens = 2000 + i * 1100;
    const name = names[i] ?? `Agent ${i}`;
    agents.push(
      makeAgent(`agent-${i}`, name, offset, offset + duration, tokens)
    );
    totalTokens += tokens;
    offset += duration + 1;
  }

  const transcript = makeAgent(
    "transcript",
    "Transcript",
    0,
    offset,
    totalTokens,
    agents
  );

  return {
    name: "Many rows (8+)",
    description: "S8 — Tests 6-row cap / scrolling with 10 agents",
    nodes: makeNodes(transcript),
  };
}

// S10: Utility agents
function utilityAgents(): TimelineScenario {
  const util1 = makeAgent("util-1", "bash_checker", 3, 4, 300, [], {
    utility: true,
  });
  const util2 = makeAgent("util-2", "safety_validator", 8, 9, 200, [], {
    utility: true,
  });
  const util3 = makeAgent("util-3", "bash_checker", 14, 15, 300, [], {
    utility: true,
  });
  const util4 = makeAgent("util-4", "format_checker", 20, 21, 250, [], {
    utility: true,
  });
  const mainAgent = makeAgent("main", "Build", 2, 45, 28000, [
    util1,
    util2,
    util3,
    util4,
  ]);

  const transcript = makeAgent("transcript", "Transcript", 0, 50, 29050, [
    mainAgent,
  ]);

  return {
    name: "Utility agents",
    description: "S10 — Agent with multiple utility children",
    nodes: makeNodes(transcript),
  };
}

// S11a: Branches (single fork)
function branchesSingleFork(): TimelineScenario {
  const branch1: BranchType = {
    type: "branch",
    forkedAt: "model-call-5",
    content: [
      makeAgent("branch1-refactor", "Refactor", 15, 22, 5200),
      makeAgent("branch1-validate", "Validate", 23, 28, 3500),
    ],
    startTime: ts(BASE, 15),
    endTime: ts(BASE, 28),
    totalTokens: 8700,
  };

  const branch2: BranchType = {
    type: "branch",
    forkedAt: "model-call-5",
    content: [makeAgent("branch2-rewrite", "Rewrite", 15, 25, 5100)],
    startTime: ts(BASE, 15),
    endTime: ts(BASE, 25),
    totalTokens: 5100,
  };

  const code = makeAgent("code", "Code", 2, 24, 15200);
  const test = makeAgent("test", "Test", 25, 40, 10400);

  const build = makeAgent("build", "Build", 1, 52, 31800, [code, test], {
    branches: [branch1, branch2],
  });

  const transcript = makeAgent("transcript", "Transcript", 0, 55, 31800, [
    build,
  ]);

  return {
    name: "Branches (single fork)",
    description: "S11 — Agent with 2 branches at one fork point",
    nodes: makeNodes(transcript),
  };
}

// S11b: Branches (multiple forks)
function branchesMultipleForks(): TimelineScenario {
  const earlyBranch: BranchType = {
    type: "branch",
    forkedAt: "model-call-3",
    content: [makeAgent("early-attempt", "Attempt", 8, 14, 4200)],
    startTime: ts(BASE, 8),
    endTime: ts(BASE, 14),
    totalTokens: 4200,
  };

  const lateBranch1: BranchType = {
    type: "branch",
    forkedAt: "model-call-10",
    content: [makeAgent("late-retry", "Retry", 30, 38, 3800)],
    startTime: ts(BASE, 30),
    endTime: ts(BASE, 38),
    totalTokens: 3800,
  };

  const lateBranch2: BranchType = {
    type: "branch",
    forkedAt: "model-call-10",
    content: [makeAgent("late-alt", "Alternative", 30, 42, 6100)],
    startTime: ts(BASE, 30),
    endTime: ts(BASE, 42),
    totalTokens: 6100,
  };

  const code = makeAgent("code", "Code", 2, 28, 15200);
  const test = makeAgent("test", "Test", 29, 48, 10400);

  const build = makeAgent("build", "Build", 1, 55, 31800, [code, test], {
    branches: [earlyBranch, lateBranch1, lateBranch2],
  });

  const transcript = makeAgent("transcript", "Transcript", 0, 58, 31800, [
    build,
  ]);

  return {
    name: "Branches (multiple forks)",
    description: "S11 — Agent with branches at different fork points",
    nodes: makeNodes(transcript),
  };
}

// ---------------------------------------------------------------------------
// Export all scenarios
// ---------------------------------------------------------------------------

export const timelineScenarios: TimelineScenario[] = [
  sequentialAgents(),
  iterativeAgents(),
  deepNesting(),
  parallelAgents(),
  inlineMarkers(),
  flatTranscript(),
  manyRows(),
  utilityAgents(),
  branchesSingleFork(),
  branchesMultipleForks(),
];
