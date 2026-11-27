; Inno Setup 6 installer script
#define MyAppName "Bulk Metadata Editor"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Bulk Metadata Editor"
#define MyAppExeName "BulkMetadataEditor.exe"

[Setup]
AppId={{8B6D19D2-7D1B-4B2D-9D67-4D7A4A9B31E1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Bulk Metadata Editor
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\release
OutputBaseFilename=BulkMetadataEditor-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\{#MyAppExeName}
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\BulkMetadataEditor\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Bulk Metadata Editor"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Bulk Metadata Editor"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Bulk Metadata Editor"; Flags: postinstall nowait skipifsilent
