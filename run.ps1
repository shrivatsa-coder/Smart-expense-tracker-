Write-Host "===================================================" -ForegroundColor Cyan
Write-Host " Starting SmartSpend - Smart Expense Tracker Server" -ForegroundColor Green
Write-Host " URL: http://127.0.0.1:5000" -ForegroundColor Yellow
Write-Host "===================================================" -ForegroundColor Cyan

Start-Process "http://127.0.0.1:5000"
& "C:\Users\Sajan\AppData\Local\Python\pythoncore-3.14-64\python.exe" app.py
