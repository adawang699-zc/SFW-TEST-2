---
phase: 02-protocol-extension
plan: 02
subsystem: DNP3
tags: [protocol, scada, power-systems, windows-only, ctypes, subprocess-isolation]
duration: 15 minutes
completed_date: 2026-04-07

key-decisions:
  - decision: "Subprocess isolation for DNP3 server"
    rationale: "ctypes-based dnp3protocol.dll can crash; subprocess isolation prevents Flask agent crash"
  - decision: "In-process client operations"
    rationale: "Client operations are short-lived; acceptable risk for simplicity"
  - decision: "Windows-only with clear error messages"
    rationale: "dnp3protocol.dll is Windows-only; return helpful errors on Linux"

requires: [dnp3protocol.dll, Windows platform]
provides: [DNP3 client API, DNP3 server subprocess management]
affects: [industrial_protocol_agent.py]
---

# Phase 02 Plan 02: DNP3 Protocol Integration Summary

## One-liner
DNP3 SCADA protocol integration with subprocess-isolated server for stability on Windows platforms.

## What Was Built

### Files Created
1. **packet_agent/dnp3_server_win.py** (361 lines)
   - Standalone subprocess script for DNP3 outstation
   - Reads JSON config from stdin
   - Uses ctypes to call dnp3protocol.dll
   - Implements callbacks for Write, Select, Operate, Restart
   - Reports status via stdout JSON

2. **packet_agent/dnp3_handler.py** (588 lines)
   - `Dnp3Client` class for client operations (connect, read, write, direct_operate)
   - `Dnp3SubprocessHandler` class for server subprocess management
   - Platform and library availability detection
   - Thread-safe locks for concurrent access
   - Function codes list for frontend use

3. **packet_agent/industrial_protocol_agent.py** (modified, +357 lines)
   - 10 new Flask routes for DNP3 client/server operations
   - Global state management with locks
   - Error handling for unsupported platforms

### API Endpoints

**Client Routes:**
- `POST /api/industrial_protocol/dnp3_client/connect` - Connect to DNP3 outstation
- `POST /api/industrial_protocol/dnp3_client/disconnect` - Disconnect client
- `GET /api/industrial_protocol/dnp3_client/status` - Get connection status
- `POST /api/industrial_protocol/dnp3_client/read` - Class0 poll/read
- `POST /api/industrial_protocol/dnp3_client/write` - Write to DNP3 object
- `POST /api/industrial_protocol/dnp3_client/direct_operate` - Direct operate command
- `GET /api/industrial_protocol/dnp3_client/function_codes` - List supported function codes

**Server Routes:**
- `POST /api/industrial_protocol/dnp3_server/start` - Start outstation subprocess
- `POST /api/industrial_protocol/dnp3_server/stop` - Stop outstation subprocess
- `GET /api/industrial_protocol/dnp3_server/status` - Get subprocess status

## Deviations from Plan

None - plan executed exactly as written.

## Technical Details

### Architecture
```
[Django Web] -> [industrial_protocol_agent.py]
                    |
                    +-> [Dnp3Client] -> ctypes -> dnp3protocol.dll (in-process)
                    |
                    +-> [Dnp3SubprocessHandler] -> subprocess -> [dnp3_server_win.py]
                                                                      |
                                                                      +-> ctypes -> dnp3protocol.dll
```

### DNP3 Objects Configured
- Binary Input (Group 1) - 10 points default
- Analog Input (Group 30) - 10 points default
- Binary Output (Group 12) - 10 points, SBO mode
- Analog Output (Group 40) - 10 points, SBO mode

### Supported Function Codes
- Read (Class0 poll)
- Write
- Select / Operate
- Direct_Operate / Direct_Operate_No_ACK
- Immediate_Freeze variants
- Cold_Restart / Warm_Restart
- Delay_Measurement
- Enable/Disable_Spontaneous_Msg
- Record_Current_Time

## Verification

### Import Test
```
[OK] DNP3 handler loaded (Windows, dnp3protocol.dll available)
DNP3_AVAILABLE=True, DNP3_PLATFORM_OK=True
```

### Syntax Check
All files pass Python syntax validation.

## Commits

| Hash | Message |
|------|---------|
| 83df2d4 | feat(02-dnp3): create DNP3 subprocess server script |
| 9ebe793 | feat(02-dnp3): create DNP3 handler module |
| e08bda4 | feat(02-dnp3): add DNP3 Flask routes to agent |

## Known Limitations

1. **Windows-only**: Requires dnp3protocol.dll (Windows DLL)
2. **Subprocess isolation required**: ctypes crashes must not affect main process
3. **Library dependency**: Requires `pip install dnp3protocol` on Windows

## Next Steps

- Test with actual DNP3 master/outstation devices
- Add data point configuration API
- Implement unsolicited response handling
- Add IIN (Internal Indication) monitoring