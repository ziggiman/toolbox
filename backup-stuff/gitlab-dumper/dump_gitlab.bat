@echo off

REM Run from Windows scheduler
REM Argument is gitlab key
REM Script is using the gitlab_backup.py script 

setlocal

set gitlabKey=%1
set retentionDays=30


REM ##### Get the day-number of year #####
set "daysPerMonth=0 31 28 31 30 31 30 31 31 30 31 30"
for /F "tokens=1-3" %%a in ('wmic Path Win32_LocalTime Get Day^,Month^,Year') do (
   set /A "dayOfYear=%%a, month=%%b, leap=!(%%c%%4)*(((month-3)>>31)+1)" 2>NUL
)
set /A "i=1, dayOfYear+=%daysPerMonth: =+(((month-(i+=1))>>31)+1)*%+leap"


REM ##### Figure out which folder to use #####
set /A folderName=dayOfYear %% retentionDays

mkdir .\%folderName%


REM ##### Run backup #####
python.exe ".\gitlab_backup.py" "https://gitlab.com/api/v4" %gitlabKey% .\%folderName%


REM ##### Delete existing backup #####
del %folderName%.rar


REM ##### Compress folder and clean up #####
Rar.exe a -df -r %folderName%.rar %folderName%

echo %date% backed up into %folderName%.rar >> logfile.txt