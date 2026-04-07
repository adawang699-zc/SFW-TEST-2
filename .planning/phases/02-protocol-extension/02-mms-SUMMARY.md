---
phase: 02-protocol-extension
plan: 04
subsystem: MMS/IEC 61850
tags: [protocol, iec61850, substation, compiled-library, graceful-degradation]
duration: 8 minutes
completed_date: 2026-04-07

key-decisions:
  - decision: "Graceful degradation when pyiec61850 unavailable"
    rationale: "pyiec61850 requires manual CMake build of libiec61850; many systems won't have it compiled"
  - decision: "Thread-based server with lock protection"
    rationale: "MMS server runs in daemon thread; threading.Lock protects server instance management"
  - decision: "Clear build instructions in error messages"
    rationale: "Users need explicit guidance to build libiec61850 with Python bindings"

requires: [pyiec61850 (optional, requires libiec61850 build)]
provides: [MMS client API, MMS server simulation, IEC 61850 data model]
affects: [industrial_protocol_agent.py]
---

# Phase 02 Plan 04: MMS/IEC 61850 Protocol Integration Summary

## One-liner
MMS/IEC 61850 substation protocol integration with graceful degradation when pyiec61850 compiled bindings unavailable.

## What Was Built

### Files Created
1. **packet_agent/mms_handler.py** (485 lines)
   - MmsHandler class for client/server operations
   - pyiec61850 availability detection with multiple path search
   - Clear build instructions when library unavailable
   - Thread management for IedServer operations
   - Client read/write/connect operations
   - Domain list retrieval for server discovery

### Files Modified
2. **packet_agent/industrial_protocol_agent.py** (+229 lines)
   - MMS/IEC 61850 imports after BACnet imports
   - Global state variables (mms_servers, mms_server_lock)
   - 7 Flask routes for MMS operations

### API Endpoints

**Client Routes:**
- `POST /api/industrial_protocol/mms_client/read` - Read MMS variable
- `POST /api/industrial_protocol/mms_client/write` - Write MMS variable
- `POST /api/industrial_protocol/mms_client/connect` - Test connection
- `POST /api/industrial_protocol/mms_client/get_domains` - Get LogicalDevice list

**Server Routes:**
- `POST /api/industrial_protocol/mms_server/start` - Start IED simulator
- `POST /api/industrial_protocol/mms_server/stop` - Stop IED simulator
- `GET /api/industrial_protocol/mms_server/status` - Get server status

## Deviations from Plan

None - plan executed exactly as written.

## Technical Details

### Architecture
```
[Django Web] -> [industrial_protocol_agent.py]
                    |
                    +-> [MmsHandler] -> pyiec61850 (compiled)
                                           |
                                           +-> libiec61850 C library
                                           |
                                           +-> IEC 61850 MMS protocol
```

### MMS Variable Format
- Format: "LogicalDevice/LogicalNode$FunctionalConstraint$DataAttribute"
- Example: "MMS_SIMDevice1/GGIO1$ST$Ind1$stVal"
- LogicalNode types: GGIO (Generic I/O), MMXU (Measuring), XSWI (Switch)
- FunctionalConstraints: ST (Status), MX (Measurable), CO (Control), SP (Setting)

### pyiec61850 Search Paths
1. packet_agent/libiec61850-1.6/build/pyiec61850
2. apps/MMS/libiec61850-1.6/build/pyiec61850
3. Project root libiec61850-1.6/build/pyiec61850
4. System installed (pip install pyiec61850)

## Verification

### Import Test
```
[WARNING] pyiec61850 not available - MMS functionality disabled: No module named 'pyiec61850'
[MMS] Build instructions:
  1. Download libiec61850-1.6 from: https://github.com/mz-automation/libiec61850
  2. Build with CMake: cmake -DBUILD_PYTHON_BINDINGS=ON ..
  3. Copy pyiec61850 to packet_agent/ or install via pip
[OK] MMS handler imported (availability=False)
MMS_AVAILABLE=False
mms_handler.is_available()=False
```

### Syntax Check
All files pass Python syntax validation.

## Commits

| Hash | Message |
|------|---------|
| a37153a | feat(02-mms): create MMS handler module with availability check |
| 68bafde | feat(02-mms): add MMS Flask routes to industrial_protocol_agent.py |

## Known Limitations

1. **pyiec61850 requires compilation**: libiec61850 must be built with `-DBUILD_PYTHON_BINDINGS=ON`
2. **Library may not be available on all systems**: Windows/Linux requires manual build
3. **Default IED model**: Basic GGIO logical nodes; extended model requires config parameter
4. **MMS port 102**: May conflict with other services on port 102

## Build Instructions for pyiec61850

```bash
# 1. Download libiec61850
git clone https://github.com/mz-automation/libiec61850
cd libiec61850

# 2. Create build directory
mkdir build && cd build

# 3. Configure with Python bindings
cmake -DBUILD_PYTHON_BINDINGS=ON ..

# 4. Build
cmake --build .

# 5. Copy pyiec61850 to packet_agent/
cp pyiec61850/*.py ../../../djangoProject/packet_agent/
cp pyiec61850/*.dll ../../../djangoProject/packet_agent/  # Windows
cp pyiec61850/*.so ../../../djangoProject/packet_agent/   # Linux
```

## Next Steps

- Build pyiec61850 for actual testing
- Test with real IEC 61850 IED devices
- Add more logical node types (MMXU, XSWI, etc.)
- Implement IEC 61850 report/control blocks
- Add dataset configuration API