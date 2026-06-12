---
name: fix-bug
description: >
  Systematically fix bugs, errors, crashes, and unexpected behavior. Use this skill whenever the user
  reports something is broken, not working, throwing an error, crashing, or behaving incorrectly — even
  if they just paste a stack trace, an error message, or say "this doesn't work" without much detail.
  Also use when the user asks to fix a specific issue, resolve a bug report, or patch a regression.
  Do NOT use for feature requests, refactoring, or code style changes.
---

# Fix Bug — Systematic Bug Fixing Workflow

This skill guides you through a four-phase process to fix bugs reliably: **Reproduce → Locate → Fix → Verify**.
Each phase has a clear exit condition — don't move on until it's met.

## Phase 1: Reproduce

Understand exactly what's going wrong before touching any code.

1. **Gather context from the user's message:**
   - Error message or stack trace
   - What they expected to happen vs. what actually happened
   - Steps they took to trigger the bug
   - Environment details (browser, runtime, OS) if relevant

2. **If information is missing,** ask ONE focused question — not a laundry list. Example:
   - "Can you paste the full error message?" (if only a partial error was given)
   - "What URL or input triggers this?" (if the trigger is unclear)
   - "Is this in dev or production?" (if environment matters)

3. **Reproduce the bug:**
   - Read the relevant source files to understand the code path
   - If there are tests, run them: `npm test`, `pytest`, `go test`, etc.
   - If the app can be started locally, start it and try to trigger the bug
   - If you can't reproduce it, say so and explain what you tried — don't pretend

**Exit condition:** You can clearly state: "The bug is [X]. It happens when [Y]."

## Phase 2: Locate

Find the exact root cause. A fix without understanding the cause is a guess.

1. **Trace the code path** from the trigger point (user input, API call, event) to the failure point (error, wrong output, crash)
2. **Use targeted searches** — grep for error messages, function names, variable names mentioned in the stack trace
3. **Check common root causes:**
   - Null/undefined access
   - Type mismatches (string vs number, missing fields)
   - Off-by-one errors, wrong comparison operators
   - Missing error handling (unhandled promise rejection, unchecked return values)
   - State management issues (stale closures, race conditions, missing re-renders)
   - Configuration problems (wrong env vars, missing dependencies, version conflicts)
4. **If multiple possible causes exist,** list them with your confidence level and investigate the most likely one first

**Exit condition:** You can clearly state: "The root cause is [X] at [file:line]. It happens because [explanation]."

## Phase 3: Fix

Implement the minimal, correct fix. Resist the urge to refactor or "improve" surrounding code.

1. **Make the smallest change** that correctly fixes the root cause
   - Fix one bug at a time — if you discover additional issues, note them but don't fix them in this pass
   - Don't change unrelated code, even if it "could be better"
   - Don't add features or "nice-to-haves"

2. **Fix the actual cause, not the symptom:**
   - Bad: wrapping a crashing call in a try/catch and ignoring the error
   - Good: fixing why the value is null in the first place
   - Bad: adding a setTimeout to "fix" a race condition
   - Good: properly awaiting the async operation or using correct state synchronization

3. **Preserve existing behavior** — the fix should not break other functionality
   - Check if the code you're changing is used elsewhere
   - If the fix might have side effects, document them

**Exit condition:** The code change is made and you can explain why it fixes the root cause.

## Phase 4: Verify

Prove the fix works. No verification = no confidence.

1. **Run existing tests** to confirm nothing is broken
2. **If there's a relevant test file,** add a regression test that:
   - Reproduces the original bug (would fail without the fix)
   - Passes with the fix applied
3. **If the app can be started,** start it and manually verify the fix addresses the reported issue
4. **Report the result:**
   - What was wrong (root cause)
   - What you changed (the fix)
   - How you verified it works

**Exit condition:** Tests pass and/or manual verification confirms the bug is fixed.

## Communication Style

- After each phase, briefly state what you found — don't go silent for long periods
- If a phase takes more than a few steps, give a progress update
- When the fix is complete, provide a concise summary:
  ```
  根因：[one line]
  修复：[one line describing the change]
  验证：[what you ran / checked]
  ```

## When Things Don't Go As Planned

- **Can't reproduce:** Say so clearly. Share what you tried and ask for more details
- **Root cause is ambiguous:** Present the top candidates with your reasoning, let the user weigh in
- **Fix is risky or large:** Explain the trade-offs before proceeding. A big fix might mean the diagnosis is wrong
- **Bug is in a dependency:** Identify which dependency and suggest workarounds or upstream fixes
