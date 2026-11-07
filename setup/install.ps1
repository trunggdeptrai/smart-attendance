# Smart Attendance - bo cai dat tu dong (goi tu CAI_DAT_SMART_ATTENDANCE.bat)
# Cac buoc: kiem tra Windows -> cai Python 3.11 (neu chua co) -> tao .venv -> cai thu vien
#           -> khoi tao du lieu -> dat mat khau -> tao loi tat Desktop -> mo ung dung.
# Khong xoa du lieu co san: .venv sai phien ban duoc doi ten, khong bi xoa.

param([switch]$NoShortcut, [switch]$NoLaunch)  # 2 tuy chon chi dung khi kiem thu
$ErrorActionPreference = "Continue"
# Hien dung tieng Viet khi Python in ra (neu khong se thanh dau ?)
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch {}
$OutputEncoding = [Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
$PythonVersion = "3.11.9"
$PythonUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-amd64.exe"

$SetupDir = $PSScriptRoot
$Root = Split-Path -Parent $SetupDir
$Step = 0

function Buoc($text) {
    $script:Step++
    Write-Host ""
    Write-Host "[$script:Step/7] $text" -ForegroundColor Cyan
}

function Loi($text) {
    Write-Host ""
    Write-Host "LOI: $text" -ForegroundColor Red
    exit 1
}

function Test-Python311($exe) {
    if (-not $exe -or -not (Test-Path $exe)) { return $false }
    try {
        & $exe -c "import sys, struct; raise SystemExit(0 if sys.version_info[:2] == (3, 11) and struct.calcsize('P') == 8 else 1)" 2>$null
        return ($LASTEXITCODE -eq 0)
    } catch { return $false }
}

function Find-Python311 {
    $candidates = @(
        "$env:ProgramFiles\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
    )
    foreach ($key in "HKLM:\SOFTWARE\Python\PythonCore\3.11\InstallPath", "HKCU:\SOFTWARE\Python\PythonCore\3.11\InstallPath") {
        try {
            $item = Get-ItemProperty -Path $key -ErrorAction Stop
            if ($item.ExecutablePath) { $candidates = @($item.ExecutablePath) + $candidates }
        } catch {}
    }
    try {
        $fromPy = & py -3.11 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $fromPy) { $candidates = @($fromPy.Trim()) + $candidates }
    } catch {}
    foreach ($c in $candidates) { if (Test-Python311 $c) { return $c } }
    return $null
}

Write-Host "==============================================" -ForegroundColor Green
Write-Host "   CAI DAT SMART ATTENDANCE (diem danh hoc sinh)" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Green
Write-Host "Thu muc du an: $Root"

# ---------- 1. Kiem tra ----------
Buoc "Kiem tra may tinh va thu muc"
if (-not [Environment]::Is64BitOperatingSystem) { Loi "Can Windows 64-bit. May nay la 32-bit nen khong cai duoc." }
if (-not (Test-Path (Join-Path $Root "app.py"))) {
    Loi "Khong thay app.py ben canh thu muc setup. Hay GIAI NEN toan bo tep ZIP (chuot phai -> Extract All, chon C:\SmartAttendance) roi chay lai tu thu muc da giai nen, khong chay truc tiep trong tep ZIP."
}
if ($Root -match '\\Temp\\(Temp\d+_|Rar\$|7z)') {
    Loi "Dang chay ben trong tep ZIP/thu muc tam. Hay giai nen ZIP (chuot phai -> Extract All, chon C:\SmartAttendance) roi chay lai."
}
try {
    Get-ChildItem -Path $Root -Recurse -File -ErrorAction SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue
} catch {}
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
try {
    Invoke-WebRequest -Uri "https://pypi.org/simple/pip/" -UseBasicParsing -Method Head -TimeoutSec 20 -ErrorAction Stop | Out-Null
    Write-Host "Ket noi Internet: OK"
} catch {
    Loi "Khong ket noi duoc Internet (pypi.org). Can mang de tai thu vien lan dau. Kiem tra Wi-Fi roi chay lai."
}
$free = (Get-PSDrive -Name ($Root.Substring(0, 1)) -ErrorAction SilentlyContinue).Free
if ($free -and $free -lt 3GB) { Loi ("O dia con trong {0:N1} GB, can it nhat 3 GB." -f ($free / 1GB)) }

# ---------- 2. Python 3.11 ----------
Buoc "Kiem tra Python 3.11"
$python = Find-Python311
if ($python) {
    Write-Host "Da co Python 3.11: $python"
} else {
    Write-Host "Chua co Python 3.11 -> tai ban chinh thuc tu python.org ($PythonVersion, ~25 MB)..."
    $installer = Join-Path $env:TEMP "python-$PythonVersion-amd64.exe"
    try {
        $ProgressPreference = "SilentlyContinue"
        Invoke-WebRequest -Uri $PythonUrl -OutFile $installer -UseBasicParsing -ErrorAction Stop
    } catch { Loi "Tai Python that bai: $($_.Exception.Message)" }
    $sig = Get-AuthenticodeSignature $installer
    if ($sig.Status -ne "Valid" -or $sig.SignerCertificate.Subject -notlike "*Python Software Foundation*") {
        Remove-Item $installer -Force -ErrorAction SilentlyContinue
        Loi "Tep cai Python khong co chu ky hop le cua Python Software Foundation - da huy de an toan."
    }
    Write-Host "Dang cai Python (1-3 phut, khong tat cua so)..."
    $p = Start-Process -FilePath $installer -Wait -PassThru -ArgumentList @(
        "/quiet", "InstallAllUsers=1", "PrependPath=1", "Include_launcher=1",
        "InstallLauncherAllUsers=1", "Include_test=0", "Include_doc=0", "Shortcuts=0")
    Remove-Item $installer -Force -ErrorAction SilentlyContinue
    if ($p.ExitCode -ne 0) { Loi "Cai Python that bai (ma loi $($p.ExitCode)). Thu khoi dong lai may roi chay lai." }
    $python = Find-Python311
    if (-not $python) { Loi "Da cai Python nhung khong tim thay python.exe. Khoi dong lai may roi chay lai tep cai dat." }
    Write-Host "Da cai Python: $python"
}

# ---------- 3. Moi truong ao ----------
Buoc "Tao moi truong Python rieng cho du an (.venv)"
$venv = Join-Path $Root ".venv"
$venvPy = Join-Path $venv "Scripts\python.exe"
if ((Test-Path $venv) -and -not (Test-Python311 $venvPy)) {
    $old = "$venv" + "_cu_" + (Get-Date -Format "yyyyMMdd_HHmmss")
    Write-Host ".venv cu bi hong hoac sai phien ban -> doi ten thanh $(Split-Path -Leaf $old) (khong xoa)."
    try { Rename-Item -Path $venv -NewName (Split-Path -Leaf $old) -ErrorAction Stop } catch { Loi "Khong doi ten duoc .venv cu (dang co chuong trinh dung no?). Dong cac cua so ung dung roi chay lai." }
}
if (-not (Test-Path $venvPy)) {
    & $python -m venv $venv
    if ($LASTEXITCODE -ne 0) { Loi "Khong tao duoc .venv. Kiem tra quyen ghi trong thu muc du an." }
}
Write-Host "OK: $venvPy"

# ---------- 4. Thu vien ----------
Buoc "Cai thu vien (lan dau mat 3-10 phut tuy toc do mang)"
& $venvPy -m pip install --upgrade pip --timeout 120 --retries 5 --disable-pip-version-check
if ($LASTEXITCODE -ne 0) { Loi "Khong cap nhat duoc pip. Kiem tra mang roi chay lai." }
& $venvPy -m pip install -r (Join-Path $Root "requirements.txt") --timeout 120 --retries 5 --disable-pip-version-check
if ($LASTEXITCODE -ne 0) { Loi "Cai thu vien that bai. Thuong do mang cham/bi chan - chay lai tep cai dat (phan da tai se khong tai lai)." }

# ---------- 5. Du lieu ----------
Buoc "Khoi tao thu muc du lieu va co so du lieu"
Push-Location $Root
& $venvPy (Join-Path $Root "check_environment.py") --create-dirs --init-db
$ok = ($LASTEXITCODE -eq 0)
Pop-Location
if (-not $ok) { Loi "Kiem tra moi truong that bai. Xem cac dong [ERROR] o tren." }

# ---------- 6. Mat khau ----------
Buoc "Tai khoan dang nhap"
$secrets = Join-Path $Root ".streamlit\secrets.toml"
if (Test-Path $secrets) {
    Write-Host "Da co tai khoan tu truoc - giu nguyen. (Doi mat khau: chay .venv\Scripts\python.exe scripts\set_password.py)"
} else {
    Write-Host "Dat ten dang nhap va mat khau cho ung dung."
    Write-Host "Mat khau: it nhat 4 ky tu, nen TAT bo go tieng Viet (Unikey/EVKey) khi go. Moi phim hien thanh dau *."
    $user = (Read-Host "Ten dang nhap (Enter = admin)").Trim()
    if (-not $user) { $user = "admin" }
    while ($user -notmatch '^[A-Za-z0-9_.@-]{1,64}$') {
        Write-Host "Ten dang nhap chi gom chu khong dau, so va _ . @ -" -ForegroundColor Yellow
        $user = (Read-Host "Ten dang nhap (Enter = admin)").Trim()
        if (-not $user) { $user = "admin" }
    }
    $done = $false
    for ($try = 1; $try -le 5 -and -not $done; $try++) {
        $s1 = Read-Host "Mat khau moi" -AsSecureString
        $s2 = Read-Host "Nhap lai mat khau" -AsSecureString
        $p1 = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($s1))
        $p2 = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($s2))
        if ($p1.Length -lt 4) {
            Write-Host "Mat khau qua ngan (moi go $($p1.Length) ky tu, can it nhat 4). Thu lai." -ForegroundColor Yellow
        } elseif ($p1 -cne $p2) {
            Write-Host "Hai lan nhap khong giong nhau. Thu lai." -ForegroundColor Yellow
        } else {
            $env:SMART_ATTENDANCE_NEW_PASSWORD = $p1
            & $venvPy (Join-Path $Root "scripts\set_password.py") --username $user --password-env SMART_ATTENDANCE_NEW_PASSWORD
            $done = ($LASTEXITCODE -eq 0)
            Remove-Item Env:\SMART_ATTENDANCE_NEW_PASSWORD -ErrorAction SilentlyContinue
        }
        $p1 = $null; $p2 = $null
    }
    if (-not $done -or -not (Test-Path $secrets)) { Loi "Chua dat duoc mat khau. Chay lai tep cai dat." }
    Write-Host "Da dat tai khoan: $user"
}
# Bo qua cau hoi email cua Streamlit o lan chay dau (neu khong, cua so se dung cho nhap)
$cred = Join-Path $env:USERPROFILE ".streamlit\credentials.toml"
if (-not (Test-Path $cred)) {
    New-Item -ItemType Directory -Force -Path (Split-Path $cred) | Out-Null
    Set-Content -Path $cred -Value "[general]`nemail = `"`"" -Encoding ASCII
}

# ---------- 7. Loi tat va mo ung dung ----------
Buoc "Tao loi tat tren Desktop va mo ung dung"
$runBat = Join-Path $Root "run.bat"
if ($NoShortcut) { Write-Host "(Kiem thu: bo qua tao loi tat)" } else { try {
    $desktop = [Environment]::GetFolderPath("Desktop")
    $shell = New-Object -ComObject WScript.Shell
    $lnk = $shell.CreateShortcut((Join-Path $desktop "Smart Attendance.lnk"))
    $lnk.TargetPath = $runBat
    $lnk.WorkingDirectory = $Root
    $lnk.IconLocation = "$env:SystemRoot\System32\shell32.dll,138"
    $lnk.Description = "Mo ung dung diem danh Smart Attendance"
    $lnk.Save()
    Write-Host "Da tao loi tat 'Smart Attendance' tren Desktop."
} catch {
    Write-Host "Khong tao duoc loi tat (khong anh huong). Lan sau mo bang run.bat trong thu muc du an." -ForegroundColor Yellow
} }

Write-Host ""
Write-Host "HOAN TAT! Ung dung dang mo trong trinh duyet: http://localhost:8501" -ForegroundColor Green
Write-Host "- Dang nhap bang tai khoan vua dat."
Write-Host "- Giu cua so den 'Smart Attendance' mo trong luc dung; dong cua so do = tat ung dung."
Write-Host "- Lan sau: bam dup loi tat 'Smart Attendance' tren Desktop."
if (-not $NoLaunch) { Start-Process -FilePath $runBat -WorkingDirectory $Root }
exit 0
