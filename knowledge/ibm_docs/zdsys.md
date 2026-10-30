# ZDSYS: Display system operating state

Source: IBM z/TPF documentation - https://www.ibm.com/docs/en/SSB23S_2025/gtpo1/cmd_zdsys.html

## Requirements and restrictions

None.

## Format

ALL
displays the operating system state for each subsystem (SS) in
a multiple database function (MDBF)
environment.

## Additional information

You can use the ZCYCL
command to change the system operating state.

## Examples

```
User: ZDSYS
System: DSYS0001I 09.02.05 THE SYSTEM IS IN NORM STATE FOR SUBSYSTEM BSS+
                           ON CO0901  CPU-B  06APR
        END OF DISPLAY+
```

```
User: zdsys all
System: DSYS0007I 15.47.13 DISPLAY STATES OF ACTIVE SUBSYSTEMS
                           ON CO0901  CPU-B  06APR
         SUBSYSTEM NAME   SYSTEM STATE
         BSS              NORM
         WP               1052
        END OF DISPLAY+
```
