# ZSTAT: Display system status

Source: IBM z/TPF documentation - https://www.ibm.com/docs/en/SSB23S_2025/gtpo1/cmd_zstat.html

## Summary

Use this command to display z/TPF system status information.

## Requirements and restrictions

None.

## Format

Dinterval
Generates a time-initiated display, where interval is
the number of minutes, from 199, between displays. An immediate response
is sent to the prime CRAS. The time-initiated responses are sent
only to the read-only (RO) console.
STOP
Stops a time-initiated display.
U
Displays information about I-stream utilization, work list counts, and status information about
the z/TPF system, such as the number of allocated and
available main storage blocks and the number of active ECBs.
GPU
Displays information about general processor (GP) utilization, I-stream
utilization, and work list counts.
NVPNAME-nvpname
Lists the name-value pair values that are in use for a
specific name-value pair name in the z/TPF system, where nvpname is the name-value pair name.
All name-value pair values that are marked as nondisplayable are
replaced by the wildcard characters (*) and included in one entry. Characters that cannot be
displayed on a console are marked as dots (.). Name-value pair names that are more than 39 characters long are not
displayed.
NVPLIST
Displays a list of the name-value pair names that are
in use in the system. You can specify these name-value pair
names on the NVPNAME parameter to see the ECBs that are using the name-value pair names.
Name-value pair names that are more than 39 characters long are not
displayed. A maximum of 6000 name-value pair names are
displayed.
ENVIRonment
Displays information about the environment settings of the z/TPF system. The following fields are shown based on the current
system environment:
TPF LEVEL
Shows the product update level.
MACHINE TYPE
Shows the machine type.
IPL ARCHITECTURE
Shows the architecture that the z/TPF system was
IPLed in.
TPF IN TEST MODE
Shows whether the z/TPF control program is in
test mode.
TAPES IN TEST MODE
Shows whether tapes are in test mode.
ENVIRONMENT
Shows the environment that the z/TPF system is
currently running in.
VM ID NAME
Shows the name of the virtual machine.
VM ID SIZE
Shows the size of the virtual machine.
LPAR NAME
Shows the name of the logical partition.
LPAR SIZE
Shows the size of the logical partition.
LPAR CAP
Shows whether there is a utilization cap for the logical partition.
LPAR WAIT COMPLETION
Shows whether the PR/SM wait completion is set.
MACHINE SIZE
Shows the size of the native machine.
UNALLOCATED MEMORY
Shows the available memory after system initialization.
DUMP
Displays dump statistics, including the following information:
The start time of the first dump that is included in the current
dump statistics.
The amount of time that was required to process the last dump.
The average time that was required to process a system (CTL) dump
and the number of dumps that were processed.
The average time that was required to process an application (OPR)
dump and the number of dumps that were processed.
The longest time that was required to process a dump and the associated
number of that dump.
CLEAR
Resets the dump statistical information that was collected by
using the DUMP parameter.
HISTory
Displays the last eight dumps that have been issued for system
error dumps.
SNAP HISTory
Displays the last 10 SNAPC dumps.
DBUG
Displays the dump capture statistics for the z/TPF dump viewer, which include the following information:
The total number of dumps that were captured for the z/TPF dump viewer.
The total number of dumps that were not captured for the z/TPF dump viewer.
The code that indicates the dump capture status by the z/TPF dump viewer. For more information,
see Table 1 in the ZDHST command
information.
The count of dumps that are associated with a status code.
The reason that certain dumps are captured or not captured for the z/TPF dump viewer.
EDAT
Displays information about the enhanced-DAT (EDAT) storage
area, with all addresses and sizes displayed in hexadecimal format.
OWNER
Displays information for a specific owner about the use of the
following resources:
Common blocks
ECBs
Input/output blocks (IOBs)
System work blocks (SWBs)
Extended system work blocks (XWBs)
4 KB frames
1 MB frames
SYSHEAP
Displays information about the usage of 31-bit system heap, 64-bit system heap, and recoverable system heap, which includes the following resources:
Size of the preallocated storage (64-bit system heap
only)
Amount of preallocated storage in use (64-bit system heap only)
Total storage in use
High-water mark of in-use storage
Amount of storage on the available list
Size of the heap
All sizes are in KB.
NAME-ownername
Specifies the owner name that you want to display the block usage or system heap storage usage information for, where
ownername is a 1- to 32-character name.
An owner name must include a 1- to
8-character high-level qualifier; optionally, it can also include a 1- to 8-character mid-level
qualifier and a 1- to 16-character low-level qualifier. Qualifiers are separated by a period (.).
You can specify a group of owner names by using the wildcard character (*) as the last character in
the owner name. You cannot specify more than one wildcard character; also, you cannot specify only a
wildcard character for the owner name.
Owner names are case sensitive. IBM® reserves owner names, including high-level qualifiers, that begin with
uppercase or lowercase I (I or i). The following list contains some of the high-level qualifiers
that are used for owner names:
IBEVQ
ICONN
ICONSOLE
ICRPA
IDASD
IDFDL
IECB
IEVENT
IFDES
IFILESYS
IMONGO
IMPIF
IMQssn, where ssn is a subsystem name
INSNA
ISERVICE
ISNA
IOPENAPI
ISYSHEAP
ISYSTEM
ITAPE
ITCPIP
ITLOG
ITPFDF
The system heap storage owner names are defined as
part of the GSYSC macro or the tpf_gsysc
function.
BLOCK-blocktype
Specifies the physical block type information that you want to
display, where blocktype is one of the following
values:
ALL
All of the following physical block types
Note: You must specify
an owner name to use the ALL option.
CMB
Common block
ECB
Entry control block
FRM
4 KB frame
FRM1MB
1 MB frame
IOB
I/O control block
SWB
System work block
XWB
Extended system work block
HIGH-number
Specifies the number of owner names that you want to display block usage or system heap storage usage information for, where
number is a value in the range 0 - 99.
The owner names that are displayed are
determined by which owner names own the highest number of blocks for the physical block types that
are specified or which owner names own the highest amount of system heap storage. If you specify 0, information is displayed for all
owner names. You cannot specify this parameter if you specify
BLOCK=ALL.
LPAR
Displays information about LPARs that are defined in the current processor.
ACTive
Displays only the active LPARs. An LPAR is considered to be active if it defines at least one
I-stream.
ALL
Displays all LPARs.
INACTive
Displays only the inactive LPARs. An LPAR is considered to be inactive if it does not define any
I-streams.
NAME-lparname
Specifies the group of LPARs that you want to display, where lparname is a 1-
to 7-character alphanumeric prefix for LPAR names that ends with an asterisk. For example, if you
specify NAME-TPF*, all of the LPARs with a name that starts with TPF are
displayed.
IOPS
Displays the number of DASD I/Os that were issued in the last second for each MDBF subsystem in the complex.
TOPology
Displays topology information about the z/TPF
LPAR, such as the I-steam drawer location.
This
parameter provides relevant data only when the z/TPF system is running on a dedicated PR/SM configuration on
IBM z16® or later. When this parameter is specified,
you can identify that I-streams in the z/TPF
logical partition (LPAR) are using central processors that reside
on more than one drawer.

## Additional information

Enter ZSTAT (without any parameters) to display status information about
the z/TPF system.
If you do an initial program load (IPL) while a time-initiated
display is active, the display is resumed with the specified time
interval when the IPL is completed.
To generate a time-initiated display for the I-stream utilization
information, use the ZSTIM command.

## Examples

```
User: WP/ZSTAT
System: STAT0041I 13.42.13 SYSTEM STATUS DISPLAY
                         RLOG     IOB   FRAME  COMMON     SWB     XWB     ECB  FRM1MB
        ALLOCATED        7040    8192    1000     400    4096    4096     600     400
        AVAILABLE        6335    8192     985     395    3839    3815     547     174
```

```
User: ZSTAT GPU
System: STAT0040I 23.27.35 SYSTEM UTILIZATION DISPLAY
        STATIC POWER SAVE MODE - SYSTEM AT 100 PERCENT
        SPEED BOOST IS NOT ACTIVE
        I-STREAM BOOST IS NOT ACTIVE
                  ACTUAL   GP      GP     GP
        NAME       UTIL   UTIL    CAP   ENGINES
        TPFP0001   70.8   42.5   100.0     2
        NUM  ADR  UTIL/ ADJ  CROSS READY INPUT   VCT SUSPD DEFER ACT-ECB S   PSU  LPUU
        IS- 1 00  90.2/ 89.7     0     1     0     0     0     3     10  U   90.2  3.2
        IS- 2 02  61.1/ 60.7     0     0     0     0     0     0     14  U   61.1   .0
        IS- 3 03  61.1/ 60.7     1     0     0     0     0     0     14  U   61.1   .0
        IS- 4 04    .2/   .2     0     0     0     0     0     0      0  P1    .2   .0
        IS- 5 05    .2/   .2     0     0     0     0     0     0      0 CP2    .2   .0
        IS- 4 03   6.1/  5.6     0     0     0     0     0     0      1 SF1   6.1  1.2
        IS- 5 04    .7/   .5     0     0     0     0     0     0      0  F1    .7   .6
        IS- 8 08    .2/   .2     0     0     0     0     0     0      0  F2    .2   .0
        END OF DISPLAY+
```

```
User: ZSTAT GPU
System: STAT0040I 23.27.35 SYSTEM UTILIZATION DISPLAY
        STATIC POWER SAVE MODE - SYSTEM AT 100 PERCENT
        SPEED BOOST IS ACTIVE UNTIL Tue Jul 16 23:32:16 2019
        I-STREAM BOOST IS ACTIVE; NEXT I-STREAM COLLAPSE IS Tue Jul 16 23:37:16 2019
                  ACTUAL   GP      GP     GP
        NAME       UTIL   UTIL    CAP   ENGINES
        TPFP0001   70.8   42.5   100.0     2
        NUM  ADR  UTIL/ ADJ  CROSS READY INPUT   VCT SUSPD DEFER ACT-ECB S   PSU  LPUU
        IS- 1 00  37.5/ 37.3     0     1     0     0     0     0     14  U   37.5   .0
        IS- 2 01  43.0/ 42.8     0     0     1     0     0     0     12  U   43.0   .0
        IS- 3 02  41.2/ 41.0     0     0     0     0     0     0     11  U   41.2   .0
        IS- 4 03  43.6/ 43.4     0     3     0     0     0     0     10  U   43.6   .0
        IS- 5 04  43.8/ 43.6     0     1     0     0     0     0     11 CU   43.8   .0
        IS- 6 05  42.7/ 42.5     1     0     0     0     0     0      9 BU   42.7   .0
        IS- 7 06  42.5/ 42.3     0     0     0     0     0     1      7 BU   42.5   .0
        IS- 8 07  42.2/ 42.0     0     0     0     0     0     0     10 BU   42.2   .0
        END OF DISPLAY+
```

```
User: ZSTAT ENVIR
System: STAT0063I 21.12.26 SYSTEM ENVIRONMENT DISPLAY

           TPF LEVEL                    2019                                      
           MACHINE TYPE                 3906-7D1                                  
           IPL ARCHITECTURE             ESA/390                                   
           TPF IN TEST MODE             YES                                       
           TAPES IN TEST MODE           YES                                       
                                                                   
           ENVIRONMENT                  VM                                        
           VM ID NAME                   TPFGI409                                  
           VM ID SIZE                   2 GB                                      
           UNALLOCATED MEMORY           0 B                                       
           HIPERDISPATCH                NO
        END OF DISPLAY+
```

```
User: ZSTAT ENVIR
System: STAT0063I 21.12.26 SYSTEM ENVIRONMENT DISPLAY

           TPF LEVEL                    2019
           MACHINE TYPE                 3906-774
           IPL ARCHITECTURE             z/Architecture
           TPF IN TEST MODE             YES
           TAPES IN TEST MODE           NO
 
           ENVIRONMENT                  PR/SM-SH
           LPAR NAME                    TPFP8
           LPAR SIZE                    128 GB
           LPAR CAP                     NO
           LPAR WAIT COMPLETION         NO
           UNALLOCATED MEMORY           0 B
           HIPERDISPATCH                NO
        END OF DISPLAY+
```

```
User: ZSTAT OWNER NAME-I* BLOCK-ALL
System: STAT0042I 13.40.57 BLOCK OWNER DISPLAY
                         RLOG     IOB   FRAME  COMMON     SWB     XWB     ECB  FRM1MB
        ALLOCATED        7040    8192    1000     400    4096    4096     600     400
        AVAILABLE        6335    8192     985     395    3839    3814     547     175
        
                                  IOB   FRAME  COMMON     SWB     XWB     ECB  FRM1MB
        ISYSTEM                     0       0       1      62      15       0       0
        IEVENT                      0       0       0     145       0       0       0
        IDSCB                       0       0       0      20       0       0       0
        IFSLOCK                     0       0       0      18       0       0       0
        ITCPIP                      0       0       0       9       0       0       4
        ISHM_TAB                    0       0       0       1       0       0       0
        INETD                       0       0       0       2      15      36      42
        ISSL                        0       0       0       0      11      10      12
        IMQ                         0       0       0       0       3       2       2
        IECB                        0       1       2       0       2       4       3
        ISMP                        0       0       2       0       2       1       0
        ICLOCKS                     0       1       0       0       0       0       0
        IHSC                        0      12       0       0       0       
```

```
User: ZSTAT OWNER NAME-I* BLOCK-SWB HIGH-5
System: STAT0042I 13.43.16 BLOCK OWNER DISPLAY
                         RLOG     IOB   FRAME  COMMON     SWB     XWB     ECB  FRM1MB
        ALLOCATED        7040    8192    1000     400    4096    4096     600     400
        AVAILABLE        6335    8192     985     395    3838    3814     547     174
        
                                  IOB   FRAME  COMMON     SWB     XWB     ECB  FRM1MB
        IEVENT                                            145
        ISYSTEM                                            62
        IDSCB                                              20
        IFSLOCK                                            18
        ITCPIP                                              9
        END OF DISPLAY+
```

```
User: ZSTAT EDAT
System: STAT0032I 16.48.28 EDAT storage area
           EDAT starting address (real)   00000000 1FE00000
           EDAT size                      00000002 38800000
           EDAT mapping
              1M frame area size          00000000 60200000
              2G frame area size          00000001 80000000
              1M frame area size          00000000 58600000
           VFA starting address (SVM)     0000000F 150A4000
           VFA starting address (real)    00000000 950A4000
           VFA size                       00000000 7D000000
           Skipped storage size           00000000 001F3000
        END OF DISPLAY+
```

```
User: ZSTAT DUMP
System: STAT0020I 09.37.58 DUMP STATISTICS DISPLAY                    
         TIME OF FIRST DUMP   -27JAN  13.29.15                         
         AVERAGE CTL DUMP (MS)-        38                              
         NUMBER OF CTL DUMPS  -         5                                    
         AVERAGE OPR DUMP (MS)-         6                              
         NUMBER OF OPR DUMPS  -         2 _                            
         LAST  DUMP (MS) -        79  NUMBER-  2017  DUMP-B6H8A       
         LONGEST DUMP (MS)  -        93  NUMBER-  2016  DUMP-B6H8A   
         DUMPS SUPRESSED (ZASER MAXCPSE) -           0                 
         CTL DUMPS NODUMPED (ZASER MAXCTL) -         0                 
         OPR DUMPS NODUMPED (ZASER MAXOPR) -         0                 
         CTL DUMPS SUPPRESSED DUE TO ZASER DBACTL -         0 _        
         OPR DUMPS SUPPRESSED DUE TO ZASER DBAOPR -         0          
         DUMPS CAPTURED FOR DUMP VIEWER  -           0                          
         DUMPS NOT CAPTURED FOR DUMP VIEWER -        9                 
         DUMPS TIMED OUT (ZASER MAXDUMPT ) -       0                   
         END OF DISPLAY+
```

```
User: ZSTAT DUMP CLEAR
System: STAT0021I 13.39.46 DUMP STATISTICS TABLE CLEARED
```

```
User: ZSTAT DUMP HIST
System: STAT0030I 15.06.18 DUMP HISTORY DISPLAY 
        SEQNUM DUMP NUMBER TRC  PGM    LOADSET  LNIATA    TIME    SS   SSU  IS    
        0001   MANUAL                           010000B 14.44.07  BSS  HPN  01    
        0002   OPR-I911A21 QTA2 QTA2   BASE     010000B 14.44.07  BSS  HPN  01 _  
        0003   OPR-U911A77 QTA7 QTA7   BASE     010000B 14.44.07  BSS  HPN  01    
        0004   CTL-I000003 QTA2 QTA2   BASE     010000B 14.44.07  BSS  HPN  01    
        0005   CTL-I000003 QSCC QSCC   BASE     010000B 08.58.28  BSS  HPN  01    
        0006   MANUAL                  TESTDUMP 010000B 08.59.02  BSS  HPN  01 _  
        0007   OPR-I911A21 QTA2 QTA2   BASE     010000B 08.59.23  BSS  HPN  01    
        0008   OPR-I911A21 QTA2 QTA2   BASE     010000B 08.59.31  BSS  HPN  01    
        END OF DISPLAY
```

```
User: ZSTAT DUMP SNAP HIST
System: STAT0031I 09.50.47 SNAP DUMP HISTORY DISPLAY            
        SNAPC NUMBER  PROGRAM  LNIATA     TIME    SS   SSU  IS  
        A00009111     QXC4     010000B   9.50.27  BSS  HPN  01  
        C00009112     QXC4     010000B   9.50.38  BSS  HPN  01  
        END OF DISPLAY
```

```
User: ZSTAT DUMP DBUG
System: STAT0038I 14.20.26 DUMP VIEWER STATISTICS DISPLAY
        DUMPS CAPTURED FOR DUMP VIEWER   -             2
        DUMPS NOT CAPTURED FOR DUMP VIEWER   -         3
        COUNT CODE REASON                                   
        1      1    Processing did not complete
        1      4    ZASER NODBUG set
        1      5    ZASER DUMPOFF set                                            
        END OF DISPLAY+
```

```
User: ZSTAT SYSHEAP
System: STAT0125I 10.29.41 SYSTEM HEAP STATISTICS DISPLAY                              
                                 31-BIT HEAP   64-BIT HEAP                             
        PREALLOCATED SIZE   (KB)         N/A        204800                             
        PREALLOCATED IN USE (KB)         N/A        121704                            
        1MB FRAME STORAGE   (KB)        3072             0                             
        HEAP STORAGE IN USE (KB)        2420        121704                             
        AVAILABLE LIST SIZE (KB)         652         83096                             
        MAX STORAGE IN USE  (KB)        2424        123240                            
        SIZE OF HEAP        (KB)     1665024        614400                             
        -------------------------------------------------                              
        RECOVERABLE SYSTEM HEAP                                                        
        -------------------------------------------------                             
        SIZE OF RECOVERABLE SYSTEM HEAP (KB)                    9437183                
        MAX 1MEG SEGMENTS IN USE SINCE LAST INIT                      5   
        NUMBER OF RECOVERABLE SYSTEM HEAP REQUESTS                   57
        NUMBER OF FAILED RECOVERABLE SYSTEM HEAP REQUESTS            43
        MINIMUM FAILED RECOVERABLE SYSTEM HEAP SIZE (MB)              0
        NUMBER OF RECOVERABLE SYSTEM HEAP FILLED BY 64 BIT            0   
 
```

```
User: ZSTAT SYSHEAP NAME-I* HIGH-5
System: STAT0126I 11.24.22 SYSTEM HEAP STORAGE OWNER DISPLAY
                                 31-BIT HEAP   64-BIT HEAP
        PREALLOCATED SIZE   (KB)         N/A        204800
        PREALLOCATED IN USE (KB)         N/A        125672 _
        1MB FRAME STORAGE   (KB)        3072             0
        HEAP STORAGE IN USE (KB)        2464        125672
        AVAILABLE LIST SIZE (KB)         608         79128
        MAX STORAGE IN USE  (KB)        2472        126696 _
        SIZE OF HEAP        (KB)     1665024        614400
        -------------------------------------------------
        RECOVERABLE SYSTEM HEAP
        ------------------------------------------------- _
        SIZE OF RECOVERABLE SYSTEM HEAP (KB)                    9437183
        MAX 1MEG SEGMENTS IN USE SINCE LAST INIT                      5
                                   TOTAL (KB)   31-BIT HEAP   64-BIT HEAP   RECOVERABLE
        _
        ILRCACHE                     55924            24         55900             0
        IMFS_FIL                     25600             0         25600             0
        IVFS_ZON                      9048             0          9048             0 _
        IVCFX_FI                      5120             0          5120             0
        ISHSHEAP                      5120             0             0          5120
        END OF DISPLAY+
```

```
User: ZSTAT LPAR ALL NAME-TP*
System: STAT0035I 10.16.26 LPAR UTILIZATION DISPLAY

         NUMBER OF LPARS - 45
         TOTAL WEIGHT OF SHARED LPARS THAT USE GENERAL CPUS - 760
         TOTAL NUMBER OF PHYSICAL CPUS - 39
         TOTAL NUMBER OF GENERAL CPUS FOR SHARED LPARS - 25
         WHITESPACE - 66.0 

          LPARNAME  RCPUs  SCPUs  TYPE  WEIGHT   UTIL  UTILVCAP   MACHINE   ENTITLE 
          TPFLINUX      2      0    D
          TPFP1        16     16     S      10   48.7                31.2    2368.4
          TPFP2         8      8     S      10    0.2                 0.1       5.1
          TPFP3         4      4     S      10    0.4                 0.1       4.9
          TPFCF1        0      0   I
          TPFP4        16     16     S      10    0.2                 0.2      12.1
          TPFP5         4      4    D
          TPFP7        11     11     S     500    0.3                 0.1       0.2
          TPFP8         1      1    D
          TPFCF2        1      0    D
          TPFCF3        0      0     S       0
         END OF DISPLAY+
```

```
User: ZSTAT NVP-MsgType
System: CSMP0097I 15.59.53 CPU-B SS-BSS  SSU-HPN  IS-01  
         STAT0102I 15.59.53 LIST OF VALUES FOR THE MsgType NAME-VALUE PAIR NAME
                            IN-USE ECBS WITHOUT THE SPECIFIED NAME IS 2
                            COUNT       VALUE
                            1        ZBOOKING
         END OF DISPLAY+
```

```
User: ZSTAT NVPLIST
System: CSMP0097I 10.05.48 CPU-B SS-BSS  SSU-HPN  IS-01                  
         STAT0104I 10.05.48 LIST OF THE IN-USE NAME-VALUE PAIR NAMES               
                            COUNT OF THE IN-USE NAMES IS 3                                   
                            ISrvcName  
                            MsgType                                                         
                            ZZZ                                                             
         END OF DISPLAY+
```

```
User: ZSTAT IOPS
System: CSMP0097I 23.18.22 CPU-B SS-BSS  SSU-HPN  IS-01
        STAT0062I 23.18.22 DASD IOPS DISPLAY

        SUBSYSTEM         TOTAL         DEVA         DEVB         DEVC         DEVD
        BSS               17140         4685        12455            0            0
        WP                   12            0           12            0            0
END OF DISPLAY+
```

```
User: ZSTAT TOP
System: CSMP0097I 23.18.22 CPU-B SS-BSS  SSU-HPN  IS-01
        STAT0064I 16.42.22 SYSTEM TOPOLOGY DISPLAY  
            LPAR NAME:    TPFP1
            ENVIRONMENT:  PR/SM-D
            NUMBER DRAWER STATUS
            IS- 1    1      U
            IS- 2    1      U
            IS- 3    1      U
            IS- 4    1     CU
            IS- 5    1     BU
            IS- 6    1      F1
        END OF DISPLAY+
```
