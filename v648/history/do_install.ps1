$ErrorActionPreference = 'Stop'
$dir  = 'C:\Program Files\Rizom Lab\RizomUV 2027.0'
# Look for the 4 staged exe files next to this script first, then fall back to the build folder.
$work = $PSScriptRoot
if (-not (Test-Path -LiteralPath (Join-Path $work 'rizomuv_new_cn.exe'))) {
    $work = 'E:\A_1\ai\wd\rizom_cn'
}
$log = Join-Path $PSScriptRoot 'install_result.txt'

$enMd5    = 'abbc69339a373f08cbc3507111d97fbf'
$finalMd5 = 'ef85533b797c7fc841e9c26bd676efae'

$stages = @(
    @{ name='main-621';  file='rizomuv_new_cn.exe';         md5='cf53e1496873dffba10983d180a0cdcf' },
    @{ name='toolbar-7'; file='rizomuv_new_cn_toolbar.exe'; md5='8018ad29b03772d8b51f8c676220e334' },
    @{ name='panel-8';   file='rizomuv_new_cn_panel.exe';   md5='651a25b166ab27091f6dcc0695756529' },
    @{ name='menu-6';    file='rizomuv_new_cn_menu6.exe';   md5='ef85533b797c7fc841e9c26bd676efae' }
)

$lines = @()
try {
    $cur = Join-Path $dir 'rizomuv.exe'
    if (-not (Test-Path -LiteralPath $cur)) { throw 'rizomuv.exe not found in install dir' }
    $curMd5 = (Get-FileHash -LiteralPath $cur -Algorithm MD5).Hash.ToLower()
    $lines += "CURRENT_MD5=$curMd5"

    if ($curMd5 -eq $finalMd5) {
        $lines += 'RESULT=ALREADY_INSTALLED'
    } elseif (Get-Process rizomuv -ErrorAction SilentlyContinue) {
        throw 'RizomUV is running, please close it and retry'
    } else {
        for ($i=0; $i -lt $stages.Count; $i++) {
            $s = $stages[$i]
            $expect = if ($i -eq 0) { $enMd5 } else { $stages[$i-1].md5 }
            $now = (Get-FileHash -LiteralPath $cur -Algorithm MD5).Hash.ToLower()
            if ($now -ne $expect) { throw "Stage $($s.name): current $now != expected $expect, abort" }

            $src = Join-Path $work $s.file
            if (-not (Test-Path -LiteralPath $src)) { throw "Stage $($s.name): source not found: $src" }
            $srcMd5 = (Get-FileHash -LiteralPath $src -Algorithm MD5).Hash.ToLower()
            if ($srcMd5 -ne $s.md5) { throw "Stage $($s.name): source md5 mismatch" }

            $ts = Get-Date -Format 'yyyyMMdd_HHmmss'
            $bak = Join-Path $dir "rizomuv_before_$($s.name)_$ts.exe"
            Copy-Item -LiteralPath $cur -Destination $bak -Force
            Copy-Item -LiteralPath $src -Destination $cur -Force
            $dst = (Get-FileHash -LiteralPath $cur -Algorithm MD5).Hash.ToLower()
            if ($dst -ne $s.md5) { throw "Stage $($s.name): installed md5 mismatch, backup: $bak" }
            $lines += "STAGE=$($s.name) OK | backup=$bak"
        }
        $lines += "INSTALLED_MD5=$((Get-FileHash -LiteralPath $cur -Algorithm MD5).Hash.ToLower())"
        $lines += 'RESULT=OK'
    }
} catch {
    $lines += 'RESULT=FAIL'
    $lines += "ERROR=$($_.Exception.Message)"
}
$lines | Set-Content -LiteralPath $log -Encoding UTF8
$lines
