# Windows gives a pid to a new process once the old process has exited and the
# last handle to it is closed. A pid record is checked (is this the process
# that was recorded?) and then stopped by number, and between the two the
# checked process could exit and its number go to another. A handle opened
# before the check and closed after the stop keeps the number on the process
# that was checked.
if (-not ('WordEndpoint.ProcessHold' -as [type])) {
    Add-Type -Namespace WordEndpoint -Name ProcessHold -MemberDefinition @'
[DllImport("kernel32.dll", SetLastError = true)]
public static extern IntPtr OpenProcess(uint access, bool inherit, uint processId);
[DllImport("kernel32.dll", SetLastError = true)]
public static extern bool CloseHandle(IntPtr handle);
'@
}

# PROCESS_QUERY_LIMITED_INFORMATION, the least access there is: an
# administrator has it on processes the SYSTEM watchdog started, where .NET's
# Process.Handle (all access) can be refused. $null when the process cannot be
# opened: it is gone, or it refuses even that.
function Open-ProcessHold([string] $ProcId) {
    if ($ProcId -notmatch '^\d+$') { return $null }
    $handle = [WordEndpoint.ProcessHold]::OpenProcess(0x1000, $false, [uint32]$ProcId)
    if ($handle -eq [IntPtr]::Zero) { return $null }
    return $handle
}

function Close-ProcessHold($Handle) {
    if ($Handle -and $Handle -ne [IntPtr]::Zero) { [void][WordEndpoint.ProcessHold]::CloseHandle($Handle) }
}
