param(
    [string]$Repository = 'suoyikehahaha/QuizScanner',
    [string]$ArtifactsDir = 'dist/release',
    [switch]$DryRun
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$init = Get-Content -LiteralPath 'quizscanner/__init__.py' -Raw -Encoding UTF8
if ($init -notmatch 'VERSION\s*=\s*"([^"]+)"') { throw 'Missing desktop version' }
$desktopVersion = $Matches[1]
$gradle = Get-Content -LiteralPath 'android-app/app/build.gradle' -Raw -Encoding UTF8
if ($gradle -notmatch 'versionName\s+"([^"]+)"') { throw 'Missing Android version' }
$androidVersion = $Matches[1]
$tag = "v$desktopVersion"
$headCommit = git rev-parse HEAD
$tagCommit = git rev-parse "$tag^{commit}"
if ($LASTEXITCODE -ne 0 -or $headCommit -ne $tagCommit) { throw 'Create a release tag at the current source commit first.' }
$assetsRoot = if ([IO.Path]::IsPathRooted($ArtifactsDir)) { $ArtifactsDir } else { Join-Path $projectRoot $ArtifactsDir }
$names = @("QuizScanner-Windows-$desktopVersion.exe", "QuizScanner-Windows-$desktopVersion.zip", "QuizScanner-Android-$androidVersion.apk", "QuizScanner-source-$tag.zip", 'THIRD-PARTY-LICENSES.zip', 'SHA256SUMS.txt')
$assets = @($names | ForEach-Object { $path = Join-Path $assetsRoot $_; if (-not (Test-Path -LiteralPath $path)) { throw "Missing release asset: $_" }; $path })
$notes = Join-Path $projectRoot "docs/releases/$tag.md"
if (-not (Test-Path -LiteralPath $notes)) { throw "Missing release notes: $notes" }
if ($DryRun) { Write-Output "Repository: $Repository; tag: $tag"; $assets; exit 0 }
gh release create $tag @assets --repo $Repository --verify-tag --title "QuizScanner $desktopVersion - Android $androidVersion" --notes-file $notes --latest
if ($LASTEXITCODE -ne 0) { throw 'Release creation failed' }
