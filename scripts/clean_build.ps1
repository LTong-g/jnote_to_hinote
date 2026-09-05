[CmdletBinding(SupportsShouldProcess)]
param(
    [switch]$IncludeDist
)

$repoRoot = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$targets = @((Join-Path $repoRoot "build"))
if ($IncludeDist) {
    $targets += Join-Path $repoRoot "dist"
}

foreach ($target in $targets) {
    $resolved = [IO.Path]::GetFullPath($target)
    $parent = [IO.Path]::GetDirectoryName($resolved)
    $leaf = [IO.Path]::GetFileName($resolved)
    if ($parent -ne $repoRoot -or $leaf -notin @("build", "dist")) {
        throw "Refusing to remove unexpected path: $resolved"
    }
    if ((Test-Path -LiteralPath $resolved) -and $PSCmdlet.ShouldProcess($resolved, "Remove build artifact directory")) {
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}
