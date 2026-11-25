$ErrorActionPreference = 'Stop'
$dir = 'C:\Program Files\Rizom Lab\RizomUV 2027.0'
$src = 'E:\A_1\ai\wd\rizom_cn\rizomuv_new_cn_panel.exe'
$log = 'E:\A_1\ai\wd\rizom_cn\install_result_panel.txt'
$lines = @()
try {
    $ts = Get-Date -Format 'yyyyMMdd_HHmmss'
    $bak = Join-Path $dir "rizomuv_before_panel_$ts.exe"

    $srcMd5 = (Get-FileHash -LiteralPath $src -Algorithm MD5).Hash.ToLower()
    $lines += "SRC_MD5=$srcMd5"
    if ($srcMd5 -ne '651a25b166ab27091f6dcc0695756529') { throw 'source md5 mismatch' }

    $cur = Join-Path $dir 'rizomuv.exe'
    $curMd5 = (Get-FileHash -LiteralPath $cur -Algorithm MD5).Hash.ToLower()
    $lines += "CURRENT_MD5=$curMd5"
    if ($curMd5 -ne '8018ad29b03772d8b51f8c676220e334') { throw 'current exe is not the expected toolbar build, abort' }

    if (Get-Process rizomuv -ErrorAction SilentlyContinue) { throw 'RizomUV is running, abort' }

    Copy-Item -LiteralPath $cur -Destination $bak -Force
    $lines += "BACKUP=$bak"
    $lines += "BACKUP_MD5=$((Get-FileHash -LiteralPath $bak -Algorithm MD5).Hash.ToLower())"

    Copy-Item -LiteralPath $src -Destination $cur -Force
    $dstMd5 = (Get-FileHash -LiteralPath $cur -Algorithm MD5).Hash.ToLower()
    $lines += "INSTALLED_MD5=$dstMd5"
    if ($dstMd5 -eq $srcMd5) { $lines += 'RESULT=OK' } else { throw 'installed md5 mismatch' }
} catch {
    $lines += "RESULT=FAIL"
    $lines += "ERROR=$($_.Exception.Message)"
}
$lines | Set-Content -LiteralPath $log -Encoding UTF8
