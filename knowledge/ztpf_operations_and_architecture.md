# IBM z/TPF System Operations and Architecture Reference

## Overview of z/Transaction Processing Facility (z/TPF)
IBM z/TPF is an ultra-high performance, high-throughput transaction processing operating system designed for mission-critical enterprise workloads handling tens of thousands of transactions per second with sub-second response times.

## System Operating States and Transitions
The z/TPF operating system functions through three distinct operational states:

1. **1052 State**:
   - The initial minimal operating state following an IPL (Initial Program Load).
   - Only the prime CRAS console (1052 / 3215 device) is operational.
   - Applications and network communication lines are disabled.
   - Used exclusively for system initialization, offline maintenance, database reorganization, and emergency repairs.

2. **CRAS State (Central Reference Active Store)**:
   - Intermediate operational state.
   - All CRAS consoles are active, but application message switching and general terminals remain offline.
   - Used for running operational utilities, keypoint verification, and preparation for full online traffic.

3. **NORM State (Normal Operational State)**:
   - The full production environment.
   - All communication networks, applications, transaction servers, and database engines are fully operational.
   - Standard transaction routing and message switching are active.

### State Transition Commands
System state changes are controlled through the `ZCYCL` command:
- `ZCYCL 1052`: Cycles down the system to 1052 state. This halts general transaction processing.
- `ZCYCL CRAS`: Transitions the system from 1052 up to CRAS state, or cycles down from NORM to CRAS state.
- `ZCYCL NORM`: Brings the system to full normal production state.

Operational Note: Any `ZCYCL` command is a critical state-change operation. In automated regression scripts, `ZCYCL` must be used with caution, and expected responses such as system state confirmation messages (`DSYS0001I`, `CYCL0001I`) must be validated.

## Entry Control Block (ECB) Architecture
The basic unit of work in z/TPF is an Entry Control Block (ECB).
- An ECB represents an active transaction thread.
- Each ECB has a dedicated private 4KB work area (CE1CR) and system-assigned storage levels (D0 through DF).
- System ECB activity is monitored via `ZDECB` (Display ECBs), `ZECBL` (ECB list), and `ZECBM` (ECB resource monitor).
- Commands altering ECB states (`ZECBL`) can terminate running work and are classified as critical state changes.

## DASD, Storage, and Database Concepts
z/TPF databases rely on high-speed Direct Access Storage Devices (DASD):
- **FARF (File Address Restructuring Facility)**:
  - FARF3, FARF4, FARF5, and FARF6 represent virtual and physical address translations for 4KB database records.
  - Conversion between physical cylinder/head/record (MCHR) and FARF addresses is managed via `ZCSON`.
- **FACE / FCTB (File Address Compute Program / Table)**:
  - Defines the layout, record types, and ordinal ranges for all fixed and pool files.
  - Inspected using `ZDFCT` and modified using `ZFCTB`.
- **Pool Storage Management**:
  - File pools provide dynamic record allocation for high-volume transactions.
  - Monitored via `ZDFPC` (Display File Pool Counts). Low pool warnings require immediate operator attention.
- **Record Hold Table**:
  - Prevents race conditions and duplicate record updates across multiple ECBs.
  - Monitored via `ZDRHT`.

## Memory Management and System Heaps
- Main storage is partitioned into core resident program areas, 31-bit system heaps, and 64-bit common storage pools.
- Inspected using `ZDCOR` (Display Core) and altered using `ZACOR` (Alter Core).
- Any `ZACOR` command modifies physical memory and carries extreme operational risk.

## Diagnostics and Error Handling
- System errors generate dump captures (e.g., `CORE0397I` or system abend notifications).
- Dump status is monitored via `ZDDMP` and `ZDSER`.
- Active system logs and historical events are tracked via `ZDHST`.
