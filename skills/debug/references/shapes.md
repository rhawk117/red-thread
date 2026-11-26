# Failure shapes

Read this once after framing. Pick the one shape that fits the failure and use its reproduction, its first questions and its trap. A failure that fits two shapes takes the earlier one in this file first. Agents and brief fields are the ones in the team table of the skill.

## A test or a command that fails every time

- Reproduce: the narrowest invocation that still fails, one test and not the suite.
- First questions: `code-sense` for the path from the assertion or error text to the lines that produce it; `code-lens` for what else calls those lines; `code-sense` for `git log` on the test and on the code under it.
- Usual rivals: the code is wrong; the test is wrong, because it asserts what the code no longer promises; the fixture or test data is wrong.
- Trap: editing the assertion until it passes. Decide which side is right from what callers rely on, with a citation, before either side changes.

## Many failures at once

- Reproduce: the earliest failure in the log, alone. Later failures are often its fallout.
- First questions: `code-sense` for what the failing tests share (a fixture, an import, a module, a dependency); the first error line of each failure, grouped.
- Usual rivals: one shared cause; two unrelated causes that landed together.
- Trap: one case per failing test. Treat them as one symptom until evidence splits them, then ask the owner whether the second cause is a second case.

## It fails in CI and passes here

- Reproduce: get the failing log through `code-sense` (`gh run view --log-failed`), then try to fail locally with what CI does differently: its command, its environment variables, its random seed, a clean clone.
- First questions: `code-sense` for the workflow file and the exact command CI runs; versions of the runtime and tools in CI against local ones; what CI caches; whether the test order differs.
- Usual rivals: a version difference; state that exists locally and not in a clean clone (an ignored file, an installed package, a cache); order dependence; a timing limit CI hits and a fast machine does not.
- Trap: pushing commits to see what CI does. Each push is a slow experiment that tests several things at once. If nothing fails locally, the owner can choose a bar where the cause stays a hypothesis with a CI run as its test, and that run is the owner's to start.

## It fails sometimes

- Reproduce: measure the rate first (phase 2). Then look for the input that makes it certain: a fixed seed, a fixed order, a single worker, a frozen clock.
- First questions: `code-sense` for shared state the test touches (module globals, files, ports, the clock, the network); the seed and order of a failing run.
- Usual rivals: order dependence between tests; a race; time or locale; an external service.
- Trap: a rerun that passes. With a failure rate of 3 in 20, one green run happens 85 times in 100 with nothing fixed. State in every REFUTE how many runs it takes to mean something, and ask `research-cell` for that many.

## It worked before

- Reproduce: confirm the last known good really is good, with the same command at that commit, in a worktree.
- First questions: `code-sense` for `git log` between the good commit and SHA on the failing path; lockfile changes in that range.
- The experiment: when the range is more than a few commits, one `research-cell` with EXPERIMENT `git bisect start SHA GOOD` then `git bisect run COMMAND`. A worktree is the right place for it, because bisecting moves HEAD.
- Usual rivals: a code change in the range; a dependency that moved under an unpinned or loosely pinned requirement; a change in the environment, with no commit at all.
- Trap: taking the commit that bisection names as the cause. It is where the failure starts to show. Whether that commit introduced the defect or exposed an older one is a question for phase 6.

## Wrong result, no error

- Reproduce: turn "it looks wrong" into a check that fails: one input, the expected output and the actual one. The owner supplies the expected output. Until that check exists there is nothing to debug.
- First questions: `code-lens` for the path the value takes from input to output; `code-sense` for where it is transformed, rounded, cached or defaulted.
- Usual rivals: the transformation is wrong; the input is not what is assumed; a stale cached value; the expectation is wrong.
- Trap: comparing against what the code "should" do by your own reading. The expected value is the owner's, recorded as a `decision`.

## A crash or an exception in running software

- Reproduce: the stack trace is the first evidence. Ask the owner for the whole trace and the input or request that produced it, then build the smallest call that raises the same exception.
- First questions: `code-sense` for the frame that raised and the frame that passed it the bad value, which are often different; the configuration that process ran with.
- Usual rivals: a bad value from a caller; an unhandled state (empty, missing, concurrent); an environment difference between where it ran and here.
- Trap: catching the exception where it surfaces. That hides the symptom and keeps the cause.

## It got slow

- Reproduce: a timing with a number and a baseline, run three times, on the same machine. Without a baseline, ask the owner what "fast" was and at which commit.
- First questions: `code-sense` for `git log` on the slow path; what the path does per item (queries, allocations, network calls); data size now and before.
- The experiment: `research-cell` times the path at SHA and at the baseline commit. For a suspected step, it times the path with that step stubbed out.
- Usual rivals: an algorithm that changed; work that moved inside a loop; data that grew; a dependency that got slower.
- Trap: timing once. Report each run, and treat a difference smaller than the spread between runs as no difference.

## The build, the tools or the environment fail

- Reproduce: the failing command from a clean state where that is cheap (a fresh environment, a cleared cache).
- First questions: `code-sense` for the manifest and lockfile entries of the tool or package named in the error; `web-head` for its changelog at the pinned version and the one before; what changed on the machine with no commit.
- Usual rivals: an upstream release that changed a default; a lockfile out of step with the manifest; a stale cache; the agent harness itself.
- Trap: a failure caused by the harness you run in. A sandbox that refuses a path, a network host or a nested session produces errors that look like the project's. If the error names a path or a host the sandbox restricts, say so to the owner and do not change code to get past it.

## A fix that did not hold

- Reproduce: the original failure, and then the failed fix's own evidence: what it changed and what still fails.
- First questions: what the earlier fix assumed the cause was, and which observation that assumption cannot explain. Record each earlier fix as a `ruled_out` from the owner.
- Usual rivals: the earlier cause was a symptom of a deeper one; there are two causes; the fix was right and something else reverted or bypassed it.
- Trap: a variant of the same fix. Earlier fixes count toward the three in "When a fix fails" if they were made in this case, and they are evidence either way.
