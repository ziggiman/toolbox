@echo off

REM The script takes the WSL distribution to dump as argument (use "wsl --list")
REM This script will find the number of the day of the year (like dec 24 = 358).
REM It will then do a "dayOfYear % retention" modulo calculation and place backup into folder with that name
REM 
REM To restore a backup simply run:
REM      wsl --import [distro_name] [install_location] [file_name].tar
REM  For example to create a setup called Ubuntu-18.04 from a previous WSL setup file called ubuntu.tar and then saving the setup in C:\Users\xyz\ubuntu run:
REM      wsl --import Ubuntu-20.04 C:\Users\xyz\ubuntu ubuntu.tar

setlocal

set distributionName=%1
set retentionDays=3

REM ##### Get the day-number of year #####
set "daysPerMonth=0 31 28 31 30 31 30 31 31 30 31 30"
for /F "tokens=1-3" %%a in ('wmic Path Win32_LocalTime Get Day^,Month^,Year') do (
   set /A "dayOfYear=%%a, month=%%b, leap=!(%%c%%4)*(((month-3)>>31)+1)" 2>NUL
)
set /A "i=1, dayOfYear+=%daysPerMonth: =+(((month-(i+=1))>>31)+1)*%+leap"

REM ##### Figure out which folder to use #####
set /A folderName=dayOfYear %% retentionDays

mkdir %folderName%

wsl --export %distributionName% .\%folderName%\%distributionName%.tar
