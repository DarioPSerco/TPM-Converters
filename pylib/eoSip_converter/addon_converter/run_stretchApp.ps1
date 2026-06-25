$scriptDirectory = Split-Path -Path $MyInvocation.MyCommand.Path
Set-Location $scriptDirectory
$soft_PATH = Get-Location
$libs_PATH = Join-Path $soft_PATH "libs"

Write-Output "soft_PATH=$soft_PATH"
Write-Output "libs_PATH=$libs_PATH"

# Source the environment file
. "$soft_PATH\env.ps1"

$SRV_NAME = "StretchApp"

# Java version
Write-Output ""
Write-Output "using java:"
java -version

# Set CLASSPATH
$CLASSPATH = $soft_PATH

# Adding JAR files to CLASSPATH (commented out since it's also commented out in the original script)
# Get-ChildItem "$libs_PATH\*.jar" | ForEach-Object {
#     Write-Output "add jar:$_"
#     $CLASSPATH = "$($_.FullName):$CLASSPATH"
# }

Write-Output ""
Write-Output ""
Write-Output "using CLASSPATH=$CLASSPATH"
Write-Output "using PATH=$($env:PATH)"

Write-Output ""
Write-Output "starting..."

#$exit_code = 0
#$command = "java -Dlog4j.debug=true -Djava.awt.headless=true -cp $CLASSPATH;${libs_PATH}\stretchApp.jar histogramStretcher.StretchApp $args"
#Write-Output "COMMAND: $command"
#java "-Dlog4j.debug=true" "-Djava.awt.headless=true" -cp "$CLASSPATH;${libs_PATH}\stretchApp.jar" histogramStretcher.StretchApp $args
$command = "java -cp `"$CLASSPATH;${libs_PATH}\stretchApp.jar`" histogramStretcher.StretchApp $args"
Write-Output "COMMAND: $command"
Write-Output "ARGS: $args"
Invoke-Expression $command

$exit_code = $LASTEXITCODE

if ($exit_code -eq 0) {
    Write-Output " PNG generation OK: $exit_code"
} else {
    Write-Output " PNG generation FAILURE: $exit_code"
}

Set-Location $PWD
Write-Output "BLAH exit code: $exit_code"

exit $exit_code
Write-Output "that's weird"