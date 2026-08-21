@echo off
setlocal
cd /d "%~dp0"

echo ==== %date% %time% ==== >> hhh_daily_log.txt

py coinbase_hhh_fetch.py >> hhh_daily_log.txt 2>&1
set CRYPTO_RC=%ERRORLEVEL%
if %CRYPTO_RC% NEQ 0 (
    echo [HHH DAILY] [WARN] Coinbase/crypto leg failed - exit code %CRYPTO_RC%. Continuing with last-known Crypto data. >> hhh_daily_log.txt
)

py schwab_hhh_fetch.py --template HHH_APEX_Template.html --out HHH_Latest.html >> hhh_daily_log.txt 2>&1
set SCHWAB_RC=%ERRORLEVEL%

if %SCHWAB_RC% NEQ 0 (
    echo [HHH DAILY] FAILED - schwab_hhh_fetch.py exit code %SCHWAB_RC%. >> hhh_daily_log.txt
    echo [HHH DAILY] Most likely cause: the Schwab refresh token expired ^(~weekly^). >> hhh_daily_log.txt
    echo [HHH DAILY] Fix: run "py schwab_auth.py" to re-authenticate, then re-run this task. >> hhh_daily_log.txt
    echo.
    echo HHH daily refresh FAILED — see hhh_daily_log.txt
    echo Likely fix: run "py schwab_auth.py" to re-authenticate.
) else (
    if %CRYPTO_RC% NEQ 0 (
        echo [HHH DAILY] OK with warning - HHH_Latest.html regenerated, but Crypto sleeve is STALE ^(see coinbase error above^). >> hhh_daily_log.txt
        echo HHH daily refresh OK, but the Crypto sleeve failed to update — see hhh_daily_log.txt.
    ) else (
        echo [HHH DAILY] OK - HHH_Latest.html regenerated. >> hhh_daily_log.txt
    )
    start "" "HHH_Latest.html"
)

endlocal
