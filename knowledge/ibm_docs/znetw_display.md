# ZNETW DISPLAY: Display network subarea status

Source: IBM z/TPF documentation - https://www.ibm.com/docs/en/SSB23S_2025/gtpo1/cmd_znetwdisplay.html

## Requirements and restrictions

None.

## Additional information

Online help information is available for this command. To display
the help information, enter one of the following:
ZNETW HELP
ZNETW ?
Use the ZNDLU command to display the status of individual network
addressable units (NAUs).

## Examples

```
User: ZNETW D
System: NETW0060I 08.44.42 SUBAREA DISPLAY
        NAU       TYPE      STATUS     IN-PROG
        VTAM2CTC  CDRM      INACTV     P-TRC
        VTAM3CTC  CDRM      INACTV     P-TRC
        VTAM1     CDRM      INACTV     P-TRC
        VTAM2     CDRM      INACTV     P-TRC
        VTAM6CTC  CDRM      INACTV     P-TRC
        VTAM3     CDRM      INACTV     P-TRC
        VTAM6     CDRM      INACTV     P-TRC
        TPFA      CDRM      INACTV     P-TRC
        TPFB      CDRM      ACTIVE     P-TRC
        TPFC      SSCP      ACTIVE     P-TRC
        TPFD      CDRM      INACTV     P-TRC
        TPFE      CDRM      INACTV     P-TRC
        TPFZ      CDRM      INACTV     P-TRC
        TPF0      CDRM      INACTV     P-TRC
        N30E610   NCP       INACTV     P-TRC
        N34E610   NCP       INACTV     P-TRC
        N42E431   NCP       INACTV     P-TRC
        N46E431   NCP       INACTV     P-TRC
        N50E610   NCP       INACTV     P-TRC
        N58E431   NCP       INACTV     P-TRC
        END OF SUBAREA DISPLAY
```
