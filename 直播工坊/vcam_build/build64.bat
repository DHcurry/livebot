@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
cd /d "%~dp0"
cl /LD /O2 /MT /EHsc /DWIN32 /D_WINDOWS /DUNICODE /D_UNICODE /DNDEBUG UnityCaptureFilter.cpp streams.cpp /link /DEF:UnityCaptureFilter.def /OUT:UnityCaptureFilter64.dll strmiids.lib uuid.lib ole32.lib oleaut32.lib winmm.lib advapi32.lib version.lib user32.lib gdi32.lib shell32.lib
echo BUILD_RC=%ERRORLEVEL%
