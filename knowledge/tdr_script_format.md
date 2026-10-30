# .TDR command script format

Source: IBM z/TPF documentation, ".TDR command script file type"
https://www.ibm.com/docs/en/ztpf/1.1.2025?topic=files-tdr-command-script-file-type

The .TDR file type is a variation of a command script that verifies the content of host output
responses to input messages. It is used as a regression test to confirm that existing host output
messages are still valid after changes to host operating system base code or host application code,
and it can drive more complicated automation tasks. TDR scripts are run by the RAVEN tooling.

## Record keys

- `GU:` global unexpected result string. Applies to every command in the script.
- `C:` input command sent to the host.
- `T:` timeout value in seconds. Documented as greater than 60 and less than 3600.
- `TC:` timeout value in seconds, same documented range as `T:`.
- `E:` expected result string.
- `LU:` local unexpected result string. Applies to the current command only.

## Format rules

1. Blank lines are ignored.
2. Lines that begin with `*` or `\` are comment lines and are ignored.
3. Every other line must begin with one of the keys above.
4. Each entry must be a single physical line and must not be split by carriage returns.

`E:`, `T:`, `TC:` and `LU:` lines belong to the most recent `C:` line.

## IBM example

```
C:ZDSYS MSG1
T:120
E:DSYS01I

C:ZDSYS MSG2
C:zddat

C:ZSTAT
T:10
E:allocated
E:STAT081
```

Note that the IBM example itself uses `T:10`, which is outside the documented range, so confirm what
the installed runner actually enforces.

## Team conventions (from UNIVERSAL_TDR_TEMPLATE.tdr)

- Several `E:` lines under one command mean all of the strings are required.
- Several `GU:` or `LU:` lines act as alternatives: any one of them matching is a failure.
- A `C:` with no `E:` performs no response check; use that only on purpose.
- `TC:` behaviour and other advanced keys are specific to RAVEN/TDRV; only use them when the
  execution environment supports them.
- Replace every `<PLACEHOLDER>` and review command authority and expected responses with an operator
  before running a script.
