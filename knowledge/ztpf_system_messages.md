# IBM z/TPF System Messages and Response Patterns

## Anatomy of z/TPF System Messages
IBM z/TPF messages follow a strict structural standard designed for automated console parsing and operator alerting:

```
[PREFIX][NUMBER][SEVERITY] [MESSAGE TEXT]
```

### Components
1. **Subsystem / Component Prefix (4 characters)**:
   - Identifies the functional area or program generating the message.
   - Examples:
     - `CORE`: Core control program, system abends, and memory management.
     - `STAT`: System status, processor status, and processor configuration.
     - `DSYS`: System operational state (1052, CRAS, NORM).
     - `CYCL`: System cycling controller.
     - `DMOD`: DASD module management and volume status.
     - `DFPC`: File pool counters and threshold alerts.
     - `AAEC`: TPF Operations Server communications and session handling.
     - `AAER`: RAVEN automation engine and script controller.
     - `AAES`: Terminal and message routing services.
     - `DBUG`: z/TPF debug server and code coverage.

2. **Message Identification Number (4 digits)**:
   - A unique numeric code within the component prefix (e.g., `0001`, `0397`, `0016`).

3. **Severity Indicator (1 character)**:
   - `I` (Informational): Standard operational notification indicating success or status (e.g., `CORE0397I`, `STAT0007I`).
   - `W` (Warning): Non-fatal anomaly or operational threshold reached (e.g., `AAEL0124W`).
   - `E` (Error): Command rejection, syntax error, or functional failure (e.g., `AAEC0002E`, `AAER0016E`).
   - `A` (Action): Immediate operator intervention required.
   - `D` (Decision): Operator must reply with a decision or confirmation.

## Response Verification Patterns for TDR Scripts
When building automated test scripts:
1. Always assert the specific message ID prefix and number with `I` severity when verifying successful execution.
2. Place known `E` severity codes into `LU:` (Local Unexpected) or `GU:` (Global Unexpected) to fail fast on errors.
3. Common error patterns to trap:
   - `INVALID COMMAND`
   - `COMMAND NOT AUTHORIZED`
   - `SYNTAX ERROR`
   - `PARAMETER NOT VALID`
   - `ABEND`
