# IBM z/TPF Regression Testing and RAVEN / TDR Specification

## Introduction to RAVEN and TDR
The IBM REXX Automation Variation Environment (RAVEN) and TDR test harness provide automated regression verification for z/TPF operating systems, applications, and middleware.

## Purpose of .TDR Scripts
A `.TDR` script is a structured test definition that sends sequential commands to a host z/TPF console and verifies that the system responses contain the expected strings. If an unexpected string or error is received, or if the host does not reply within the specified timeout, the test fails.

## Complete Record Key Specification

### `C:` (Command)
- **Syntax**: `C:<command_text>`
- **Description**: The exact command string dispatched to the z/TPF host console.
- **Rules**:
  - Must be a single line.
  - Characters should be uppercase or match case-sensitive command arguments.
  - Every `C:` line begins a new test step.

### `E:` (Expected Response)
- **Syntax**: `E:<substring>`
- **Description**: A string that must appear in the host console output received in response to the preceding `C:` command.
- **Rules**:
  - Multiple `E:` lines under a single `C:` line are treated as a logical AND condition: all specified strings must appear in the response buffer.
  - Can be a full message or a unique token (e.g., `E:STAT0007I`, `E:NORM STATE`).
  - Expected strings should avoid volatile content such as timestamps, CPU utilization percentages, or transient sequence counters.

### `T:` (Timeout Seconds)
- **Syntax**: `T:<seconds>`
- **Description**: Maximum number of seconds the runner waits for all expected `E:` strings to appear before declaring the step timed out.
- **Rules**:
  - Documented range: integer values > 60 and < 3600 seconds.
  - In practice, environments allow short timeouts (e.g. `T:10` or `T:30`) for fast-failing checks. The generator and validator emit warnings for out-of-range values rather than blocking valid scripts.

### `TC:` (Timeout Continue Seconds)
- **Syntax**: `TC:<seconds>`
- **Description**: Similar to `T:`, but if the timeout expires without all expected strings arriving, the runner logs a warning and continues executing the subsequent steps rather than immediately terminating the run.

### `GU:` (Global Unexpected String)
- **Syntax**: `GU:<substring>`
- **Description**: Defines an unexpected string that applies globally across all commands in the test script.
- **Rules**:
  - If a `GU:` string appears anywhere in any host response during the entire script execution, the script immediately fails.
  - Common patterns: `GU:CATALOG ERROR`, `GU:HARD FAILURE`, `GU:NOT AUTHORIZED`, `GU:ABEND`.
  - Multiple `GU:` lines act as logical OR conditions: matching ANY `GU:` causes failure.

### `LU:` (Local Unexpected String)
- **Syntax**: `LU:<substring>`
- **Description**: Defines an unexpected string that applies strictly to the current command step.
- **Rules**:
  - Must appear immediately after the relevant `C:` line (or its `E:`/`T:` attributes).
  - If the `LU:` string is matched in the output for that specific command, the step fails immediately.
  - Multiple `LU:` lines act as logical OR conditions.

## Comment and Whitespace Rules
- Lines starting with `*` or `\` are comment lines and are ignored by the runner.
- Blank lines are ignored.
- Trailing whitespace should be trimmed.
- No multiline records; each directive must be fully contained on a single physical line.
- The file encoding must be standard ASCII.
