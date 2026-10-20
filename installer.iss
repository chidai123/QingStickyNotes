; Inno Setup script for Qing Sticky Notes
#define MyAppName "轻便签"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "Qing Sticky Notes"
#define MyAppExeName "轻便签.exe"

[Setup]
AppId={{A73F9F9A-7B1A-4C88-96E3-4D23C8EDE120}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\轻便签
DefaultGroupName={#MyAppName}
OutputDir=output
OutputBaseFilename=轻便签安装程序
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\轻便签.exe
DisableProgramGroupPage=yes
SetupLogging=yes

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加选项:"; Flags: unchecked

[Files]
Source: "dist\轻便签.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\轻便签"; Filename: "{app}\轻便签.exe"
Name: "{autodesktop}\轻便签"; Filename: "{app}\轻便签.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\轻便签.exe"; Description: "立即启动轻便签"; Flags: postinstall nowait skipifsilent
