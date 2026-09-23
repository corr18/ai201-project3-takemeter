<#
    check-dataset.ps1 - sanity-check the TakeMeter labeled CSV.

    Run this every ~50 examples while annotating, and once more before you
    upload to Colab. Catches the problems that are cheap to fix now and
    expensive to discover after training.

    Usage:  powershell -ExecutionPolicy Bypass -File tools\check-dataset.ps1
#>

$ErrorActionPreference = 'Stop'

$csvPath = Join-Path $PSScriptRoot '..\data\takemeter_labeled.csv'
$VALID   = @('stat_backed', 'consensus_take', 'hot_take', 'reaction')
$TARGET  = 200
$CAP     = 70   # hard cap per planning.md section 4

if (-not (Test-Path $csvPath)) {
    Write-Host "CSV not found at $csvPath" -ForegroundColor Red
    exit 1
}

$rows = @(Import-Csv -Path $csvPath)
$problems = 0

Write-Host ""
Write-Host "TakeMeter dataset check" -ForegroundColor Cyan
Write-Host ("=" * 60)

# --- schema -----------------------------------------------------------------
if ($rows.Count -eq 0) {
    Write-Host "CSV is empty (header only). Nothing else to check." -ForegroundColor Yellow
    exit 0
}

$cols = $rows[0].PSObject.Properties.Name
foreach ($required in @('text', 'label')) {
    if ($cols -notcontains $required) {
        Write-Host "MISSING COLUMN: '$required'" -ForegroundColor Red
        $problems++
    }
}

# --- label distribution -----------------------------------------------------
Write-Host ""
Write-Host "Label distribution  ($($rows.Count) rows)" -ForegroundColor Cyan

$counts = @{}
foreach ($l in $VALID) { $counts[$l] = 0 }
$bad = @()
foreach ($r in $rows) {
    $l = ([string]$r.label).Trim()
    if ($VALID -contains $l) { $counts[$l]++ } else { $bad += $l }
}

foreach ($l in $VALID) {
    $c = $counts[$l]
    $pct = [math]::Round(100 * $c / $rows.Count, 1)
    $bar = "#" * [math]::Min(40, [int]($c / 2))
    $color = 'Gray'
    if ($c -gt $CAP) { $color = 'Red' } elseif ($c -lt 25) { $color = 'Yellow' }
    Write-Host ("  {0,-16} {1,4}  {2,5}%  {3}" -f $l, $c, $pct, $bar) -ForegroundColor $color
    if ($c -gt $CAP) {
        Write-Host "      -> over the $CAP cap from planning.md" -ForegroundColor Red
        $problems++
    }
}

if ($bad.Count -gt 0) {
    Write-Host ""
    foreach ($g in ($bad | Group-Object | Sort-Object Count -Descending)) {
        Write-Host "  INVALID LABEL '$($g.Name)' x$($g.Count)" -ForegroundColor Red
    }
    Write-Host "  Valid labels: $($VALID -join ', ')" -ForegroundColor Red
    $problems += $bad.Count
}

# --- empty text -------------------------------------------------------------
$empties = @($rows | Where-Object { -not ([string]$_.text).Trim() })
if ($empties.Count -gt 0) {
    Write-Host ""
    Write-Host "EMPTY text in $($empties.Count) row(s)" -ForegroundColor Red
    $problems += $empties.Count
}

# --- duplicates -------------------------------------------------------------
# Normalize hard: lowercase, drop punctuation/emoji, collapse whitespace.
# Two comments differing only in punctuation still leak across the split.
function Get-Norm {
    param([string]$s)
    $s = $s.ToLowerInvariant()
    $s = [regex]::Replace($s, '[^a-z0-9 ]', ' ')
    return ([regex]::Replace($s, '\s+', ' ')).Trim()
}

Write-Host ""
Write-Host "Duplicate check" -ForegroundColor Cyan

$dupGroups = @($rows | Group-Object -Property { Get-Norm ([string]$_.text) } | Where-Object { $_.Count -gt 1 })
if ($dupGroups.Count -gt 0) {
    Write-Host "  $($dupGroups.Count) duplicate group(s) - THESE LEAK ACROSS THE TRAIN/TEST SPLIT" -ForegroundColor Red
    foreach ($g in $dupGroups) {
        $uniqLabels = @($g.Group | ForEach-Object { ([string]$_.label).Trim() } | Sort-Object -Unique)
        $snip = [string]$g.Group[0].text
        if ($snip.Length -gt 70) { $snip = $snip.Substring(0, 70) + '...' }
        Write-Host ("    x{0}  [{1}]  {2}" -f $g.Count, ($uniqLabels -join '/'), $snip) -ForegroundColor Red
        if ($uniqLabels.Count -gt 1) {
            Write-Host "         ^ same text, DIFFERENT labels - annotation inconsistency" -ForegroundColor Magenta
        }
    }
    $problems += $dupGroups.Count
} else {
    Write-Host "  none" -ForegroundColor Green
}

# --- length profile ---------------------------------------------------------
Write-Host ""
Write-Host "Word count by label" -ForegroundColor Cyan
Write-Host "  (if stat_backed runs far longer than everything else, the model can" -ForegroundColor DarkGray
Write-Host "   cheat on length alone - worth noting in the README reflection)" -ForegroundColor DarkGray

foreach ($l in $VALID) {
    $texts = @($rows | Where-Object { ([string]$_.label).Trim() -eq $l } | ForEach-Object { [string]$_.text })
    if ($texts.Count -eq 0) { continue }
    $wc = @($texts | ForEach-Object { @($_ -split '\s+' | Where-Object { $_ }).Count })
    $stats = $wc | Measure-Object -Average -Minimum -Maximum
    Write-Host ("  {0,-16} avg {1,5:N1}   min {2,3}   max {3,4}" -f $l, $stats.Average, $stats.Minimum, $stats.Maximum)
}

$long = @($rows | Where-Object { @(([string]$_.text) -split '\s+' | Where-Object { $_ }).Count -gt 180 })
if ($long.Count -gt 0) {
    Write-Host "  NOTE: $($long.Count) comment(s) over ~180 words may hit DistilBERT's token limit" -ForegroundColor Yellow
}

# --- progress ---------------------------------------------------------------
Write-Host ""
Write-Host ("=" * 60)

$remaining = $TARGET - $rows.Count
if ($remaining -gt 0) {
    Write-Host "$($rows.Count)/$TARGET labeled - $remaining to go" -ForegroundColor Cyan
    $short = @($VALID | Where-Object { $counts[$_] -lt 50 } | Sort-Object { $counts[$_] })
    if ($short.Count -gt 0) { Write-Host "Prioritize: $($short -join ', ')" -ForegroundColor Yellow }
} else {
    Write-Host "$($rows.Count)/$TARGET labeled - quota met" -ForegroundColor Green
}

if ($problems -eq 0) {
    Write-Host "No problems found. Safe to upload to Colab." -ForegroundColor Green
    exit 0
} else {
    Write-Host "$problems problem(s) to fix before training." -ForegroundColor Red
    exit 1
}
