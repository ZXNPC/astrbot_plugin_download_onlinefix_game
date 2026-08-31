$ErrorActionPreference = "Stop"

$ErrorActionPreference = "Stop"

function Fetch-Json($u) {
    $r = Invoke-WebRequest -Uri $u -UseBasicParsing -TimeoutSec 30
    ($r.Content | ConvertFrom-Json) | ForEach-Object { "$($_.type) $($_.path)" }
}

"===== astrbot/core/star/register ====="
try { Fetch-Json "https://api.github.com/repos/AstrBotDevs/AstrBot/contents/astrbot/core/star/register" } catch { "ERR: $($_.Exception.Message)" }

"`n===== filter/regex.py ====="
try {
    $r = Invoke-WebRequest -Uri "https://raw.githubusercontent.com/AstrBotDevs/AstrBot/master/astrbot/core/star/filter/regex.py" -UseBasicParsing -TimeoutSec 30
    $r.Content
} catch {
    "ERR: $($_.Exception.Message)"
}
