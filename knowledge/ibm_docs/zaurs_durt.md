# ZAURS DURT: Display unit record status table

Source: IBM z/TPF documentation - https://www.ibm.com/docs/en/SSB23S_2025/gtpo1/cmd_zaursdurt.html

## Requirements and restrictions

None.

## Format

name
is the name of a unit record device, which can be CR1–CR3 for
card readers and PR1–PR7 for printers.
ALL
displays information about all the unit record devices.

## Additional information

None.

## Examples

```
User: ZAURS DURT PR1,PR2
System: AURS0050I 11.05.33 UNIT RECORD STATUS
         NAME DEV  ADR STATUS STATUS BYTES

          PR1 3211 00E        90000000
          PR2 3211 INV        90000000
```

```
User: ZAURS DURT ALL
System: AURS0050I 00.17.46 UNIT RECORD STATUS
         NAME DEV  ADR STATUS STATUS BYTES

          PR1 3211 00E        90000000
          PR2 3211 INV        90000000
          PR3 3211 INV        90000000
          PR4 3211 03E        90000000
          PR5 3211 04E        90000000
          CR1 2540 00C        50000000
          CR2 2540 00F        50000000
          CR3 2540 01F        40000000
```
