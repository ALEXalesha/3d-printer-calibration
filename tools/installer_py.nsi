; NSIS setup of the Python edition. tools/build_py.py passes VERSION, SRC, OUT, ICON.
Unicode true

!define APP "Calibrate3dPrinter"
!define TITLE "Calibrate 3D Printer"
!define PUBLISHER "ALEXalesha"
!define REGKEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP}"

Name "${TITLE}"
OutFile "${OUT}\${APP}-${VERSION}-setup.exe"
InstallDir "$LOCALAPPDATA\Programs\${APP}"
InstallDirRegKey HKCU "Software\${APP}" "InstallDir"
RequestExecutionLevel user
SetCompressor /SOLID lzma
BrandingText "${TITLE} ${VERSION}"

!include "MUI2.nsh"
!define MUI_ICON "${ICON}"
!define MUI_UNICON "${ICON}"
!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP}.exe"

!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "Russian"
!insertmacro MUI_LANGUAGE "English"

Section "Main"
  SetOutPath "$INSTDIR"
  File /r "${SRC}\*.*"
  Delete "$INSTDIR\portable.txt"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  WriteRegStr HKCU "Software\${APP}" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "${REGKEY}" "DisplayName" "${TITLE}"
  WriteRegStr HKCU "${REGKEY}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "${REGKEY}" "Publisher" "${PUBLISHER}"
  WriteRegStr HKCU "${REGKEY}" "DisplayIcon" "$INSTDIR\${APP}.exe"
  WriteRegStr HKCU "${REGKEY}" "UninstallString" "$INSTDIR\Uninstall.exe"
  WriteRegDWORD HKCU "${REGKEY}" "NoModify" 1
  WriteRegDWORD HKCU "${REGKEY}" "NoRepair" 1
  CreateDirectory "$SMPROGRAMS\${TITLE}"
  CreateShortcut "$SMPROGRAMS\${TITLE}\${TITLE}.lnk" "$INSTDIR\${APP}.exe"
  CreateShortcut "$DESKTOP\${TITLE}.lnk" "$INSTDIR\${APP}.exe"
SectionEnd

Section "Uninstall"
  Delete "$DESKTOP\${TITLE}.lnk"
  RMDir /r "$SMPROGRAMS\${TITLE}"
  RMDir /r "$INSTDIR"
  DeleteRegKey HKCU "${REGKEY}"
  DeleteRegKey HKCU "Software\${APP}"
SectionEnd
