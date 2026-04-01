; Xungungo Installer Script for Inno Setup
; =============================================
; Este script crea un instalador Windows que incluye
; Python portable y todas las dependencias.

#define MyAppName "Xungungo"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Xungungo Team"
#define MyAppURL "https://github.com/KernelPanicInc/Xungungo2"
#define MyAppExeName "xungungo.bat"

[Setup]
AppId={{8F3D9A7E-1B2C-4E5F-A8D3-7C9E2F1B5A6D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
; Archivo de licencia (descomentar si existe)
; LicenseFile=..\LICENSE
; Icono del instalador y la app
SetupIconFile=xungungo.ico
; Configuracion de salida
OutputDir=..\dist
OutputBaseFilename=xungungo-setup-{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; Privilegios (puede ser admin o lowest)
PrivilegesRequired=admin
; Arquitectura
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
; UI
UninstallDisplayIcon={app}\xungungo.ico
UninstallDisplayName={#MyAppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Python portable (descargado por GitHub Actions)
Source: "python\*"; DestDir: "{app}\python"; Flags: ignoreversion recursesubdirs createallsubdirs

; Aplicacion principal
Source: "..\run.py"; DestDir: "{app}\app"; Flags: ignoreversion
Source: "..\requirements.txt"; DestDir: "{app}\app"; Flags: ignoreversion
Source: "..\xungungo\*"; DestDir: "{app}\app\xungungo"; Flags: ignoreversion recursesubdirs createallsubdirs

; Scripts de entrada
Source: "xungungo.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "setup-env.bat"; DestDir: "{app}"; Flags: ignoreversion

; Icono
Source: "xungungo.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\xungungo.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\xungungo.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: shellexec postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\venv"
Type: filesandordirs; Name: "{app}"