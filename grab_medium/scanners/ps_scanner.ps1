param (
    [string]$TargetDir = ".",
    [string]$MediaId = "1"
)

$ErrorActionPreference = "SilentlyContinue"

# Resolve full path
$resolvedPath = [System.IO.Path]::GetFullPath($TargetDir)
if ($resolvedPath.EndsWith("\") -and $resolvedPath.Length -gt 3) {
    $resolvedPath = $resolvedPath.TrimEnd("\")
}

$delim = [char]0x1f
$scannedAt = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd HH:mm:ss")

# Use .NET EnumerateFileSystemEntries for memory-efficient streaming
try {
    $dirInfo = New-Object System.IO.DirectoryInfo($resolvedPath)
    $options = [System.IO.EnumerationOptions]::new()
    $options.RecurseSubdirectories = $true
    $options.AttributesToSkip = [System.IO.FileAttributes]::ReparsePoint # Ignore symlinks / junctions

    $entries = $dirInfo.EnumerateFileSystemInfos("*", $options)

    foreach ($entry in $entries) {
        $fullPath = $entry.FullName
        $relPath = $fullPath.Substring($resolvedPath.Length).TrimStart("\", "/")
        $relPath = $relPath -replace "\\", "/"
        $relPath = $relPath.TrimEnd("/")

        if ([string]::IsNullOrWhiteSpace($relPath)) {
            continue
        }

        $parentRelPath = ""
        $lastSlash = $relPath.LastIndexOf("/")
        if ($lastSlash -gt 0) {
            $parentRelPath = $relPath.Substring(0, $lastSlash)
        }

        $filename = $entry.Name
        $isDir = "false"
        $sizeBytes = 0
        $ext = ""

        if ($entry -is [System.IO.DirectoryInfo]) {
            $isDir = "true"
        } else {
            $isDir = "false"
            $sizeBytes = $entry.Length
            if ($entry.Extension) {
                $ext = $entry.Extension.TrimStart(".").ToLowerInvariant()
            }
        }

        $modifiedAt = $entry.LastWriteTimeUtc.ToString("yyyy-MM-dd HH:mm:ss")
        $createdAt = $entry.CreationTimeUtc.ToString("yyyy-MM-dd HH:mm:ss")

        if ([string]::IsNullOrWhiteSpace($createdAt) -or $createdAt.StartsWith("1601")) {
            $createdAt = $modifiedAt
        }

        $line = "$MediaId$delim$filename$delim$ext$delim$relPath$delim$parentRelPath$delim$isDir$delim$sizeBytes$delim$createdAt$delim$modifiedAt"
        [Console]::WriteLine($line)
    }
} catch {
    [Console]::Error.WriteLine("Error scanning directory: $_")
}
