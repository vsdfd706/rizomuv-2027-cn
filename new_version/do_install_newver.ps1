$ErrorActionPreference = 'Stop'
$dir = 'C:\Program Files\Rizom Lab\RizomUV 2027.0'
$src = 'E:\A_1\ai\wd\rizom_cn\rizomuv_new_cn.exe'
$log = 'E:\A_1\ai\wd\rizom_cn\install_result_newver.txt'
$lines = @()
try {
    $ts = Get-Date -Format 'yyyyMMdd_HHmmss'
    $bak = Join-Path $dir "rizomuv_new_en_backup_$ts.exe"

    $srcMd5 = (Get-FileHash -LiteralPath $src -Algorithm MD5).Hash.ToLower()
    $lines += "SRC_MD5=$srcMd5"
    if ($srcMd5 -ne 'cf53e1496873dffba10983d180a0cdcf') { throw 'source md5 mismatch' }

    # Verify installed file is the new English build (abbc6933)
    $curMd5 = (Get-FileHash -LiteralPath (Join-Path $dir 'rizomuv.exe') -Algorithm MD5).Hash.ToLower()
    $lines += "CURRENT_MD5=$curMd5"
    if ($curMd5 -ne 'abbc69339a373f08cbc3507111d97fbf') { throw 'current exe is not the expected new English build, abort' }

    if (Get-Process rizomuv -ErrorAction SilentlyContinue) { throw 'RizomUV is running, abort' }

    # Backup current new English version
    Copy-Item -LiteralPath (Join-Path $dir 'rizomuv.exe') -Destination $bak -Force
    $lines += "BACKUP=$bak"
    $lines += "BACKUP_MD5=$((Get-FileHash -LiteralPath $bak -Algorithm MD5).Hash.ToLower())"

    # Replace
    Copy-Item -LiteralPath $src -Destination (Join-Path $dir 'rizomuv.exe') -Force
    $dstMd5 = (Get-FileHash -LiteralPath (Join-Path $dir 'rizomuv.exe') -Algorithm MD5).Hash.ToLower()
    $lines += "INSTALLED_MD5=$dstMd5"
    if ($dstMd5 -eq $srcMd5) { $lines += 'RESULT=OK' } else { throw 'installed md5 mismatch' }
} catch {
    $lines += "RESULT=FAIL"
    $lines += "ERROR=$($_.Exception.Message)"
}
$lines | Set-Content -LiteralPath $log -Encoding UTF8
