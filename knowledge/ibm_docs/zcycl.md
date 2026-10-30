# ZCYCL: Cycle down or cycle up (change the system operating state)

Source: IBM z/TPF documentation - https://www.ibm.com/docs/en/SSB23S_2025/gtpo1/cmd_zcycl.html

## Requirements and restrictions

None.

## Format

1052
cycles the z/TPF system to
1052 state.
GFS
skips get file storage (GFS) cycle-down
during z/TPF system cycle
to 1052 state.
CRAS
cycles the z/TPF system to
CRAS state.
MESW
cycles the z/TPF system to
MESW state.
NORM
cycles the z/TPF system to
normal (NORM) state.
UTIL
cycles the z/TPF system to
utility (UTIL) state.
ALL
cycles all subsystems in a multiple database function (MDBF) environment.
(You can also specify this parameter for a non-MDBF environment.)
BP
bypasses the check of active utility functions.
INC
cycles the specified subsystems.
Note: You can specify this parameter
only in an MDBF environment.
EXC
cycles all the subsystems except the specified subsystems.
Note: You
can specify this parameter only in an MDBF environment.
ssname
is the 1- to 4-character alphanumeric name of a subsystem (MDBF
only). You can specify as many as 10 subsystem names.

## Additional information

You can cycle to the next higher state when the CRAS is inactive
by causing an external interrupt. However, when catastrophic error
recovery is being performed, causing an external interrupt will only
prevent the recovery.
Enter the ZDSYS command to display the current system state.
When you perform an IPL from the loader general
file (LGF), the z/TPF system must
be in 1052 state or UTIL state.

## Examples

```
User: ZCYCL NORM
System: CYCL0001I 10.49.46 CYCL TO NORM - STARTED+
        CSMP0097I 10.50.55 CPU-B SS-BSS  SSU-HPN  IS-01
        CJ040003I 10.50.55 TO2 CYCLED UP+
        CSMP0097I 10.50.55 CPU-B SS-BSS  SSU-HPN  IS-01
        VFAC0015I 10.50.55 DELAYED FILES ENABLED
        CSMP0097I 10.50.55 CPU-B SS-BSS  SSU-HPN  IS-01
        CVCX0001I 10.50.55 SS BSS  NOW IN NORM STATE +
```
