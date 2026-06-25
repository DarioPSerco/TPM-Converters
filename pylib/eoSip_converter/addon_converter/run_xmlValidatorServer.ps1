# this script will start the xml validator server
#
# Lavaux Gilles 07/2014
#

# Unset the DISPLAY variable
Remove-Item Env:DISPLAY -ErrorAction SilentlyContinue

# Set paths
$PREVIOUS_WD = Get-Location
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Write-Output "scriptDir=$scriptDir"
Set-Location $scriptDir
$soft_PATH = Get-Location
$libs_PATH = "$soft_PATH\libs"
Write-Output "soft_PATH=$soft_PATH"
Write-Output "libs_PATH=$libs_PATH"

# Source the environment variables
. "$soft_PATH\env.ps1"

$SRV_NAME = "xmlValidator"

# Java
Write-Output ""
Write-Output "using java:"
& java -version

# Set CLASSPATH
$CLASSPATH = $soft_PATH
Get-ChildItem "$libs_PATH\*.jar" | ForEach-Object {
    $CLASSPATH = "$($_.FullName);$CLASSPATH"
}

Write-Output ""
Write-Output ""
Write-Output "using CLASSPATH=$CLASSPATH"
Write-Output "using PATH=$env:PATH"

# Check script arguments
if ($args.Length -gt 0) {
    Write-Output "syntax run_xmlValidatorServer.ps1"
    exit
}

Write-Output ""
Write-Output "starting..."

$COMMAND = "java -cp `"$CLASSPATH`" -jar serviceServer/webServer-with-handlers.jar $env:CONFIGURATION_xmlValidator"

Write-Output "COMMAND: $COMMAND"
Invoke-Expression $COMMAND

Set-Location $PREVIOUS_WD
