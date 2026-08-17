@echo off
:: Shadow Monkey — MMM Drive Sync Launcher
:: Invoked by Windows Task Scheduler every 30 min, Mon-Fri, 6:00 AM - 11:30 AM PT
:: Output is appended to data\sync.log

cd /d "D:\Apps\DevOps\Github\monkeymatters"
python scripts\mmm_sync.py
