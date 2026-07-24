from subprocess import call

#
DEBUG = False


#
# write commands to be run with an external system command
#  param command: command to be run
#  param testExit: test the command exit code and if not 0 exit with badExitCode
#  param alias: the optional name of the command, writen to sysout in an echo 'xxx'
#
def writeShellCommand(command, testExit=False, badExitCode=-1, alias=None):
    tmp = "%s\n" % command
    mesgOK = "command succeed"
    mesgBAD = "command failed"
    if alias is not None:
        # if alias.find(' ')>=0:
        #    alias = alias.replace(' ', '_')
        mesgOK = "command: %s succeed" % alias
        mesgBAD = "command: %s failed" % alias
    if testExit:
        tmp = """%sif [ $? -ne 0 ]; then\n  echo "%s" \n  exit %s\nelse:\n  echo "%s"\n fi\n""" % (
            tmp, mesgBAD, badExitCode, mesgOK)
    return tmp


def writePowershellCommand(command, testExit=False, badExitCode=-1, alias=None):
    mesgOK = "command succeed"
    mesgBAD = "command failed"

    if alias is not None:
        mesgOK = "command: %s succeed" % alias
        mesgBAD = "command: %s failed" % alias

    if command.split()[0].endswith('.py'):
        import os
        from shutil import which
        from pathlib import Path

        command = 'python %s' % Path(which(command.split()[0])).parent + os.sep + command

    tmp = [command]
    if testExit:
        tmp += [
            'if ($LASTEXITCODE -ne 0) {',
            '    Write-Host "%s"' % mesgBAD,
            '    exit %s' % badExitCode,
            '}',
            'Write-Host "%s"' % mesgOK
        ]

    return '\n'.join(tmp) + '\n'


#
#
#
def run_shell_commands(commands, workFolder, alias):
    if alias.find(' ') >= 0:
        alias = alias.replace(' ', '_')

    commandFile = "%s/command_%s.sh" % (workFolder, alias)
    with open(commandFile, 'w') as fd:
        fd.write("""#!/bin/bash\necho starting...\n\necho "PATH is:$PATH"\n\n""")
        fd.write(commands)

    # launch the main make_browse script:
    command = "/bin/bash -f %s 2>&1 > %s/command_%s.log" % (commandFile, workFolder, alias)

    retval = call(command, shell=True)
    if DEBUG:
        print(("  external command %s exit code:%s" % (alias, retval)))
    if retval != 0:
        raise Exception("External command %s error:%s" % (alias, retval))
    print(("  external %s exit code:%s" % (alias, retval)))
    return retval


def run_powershell_commands(commands, workFolder, alias):
    if alias.find(' ') >= 0:
        alias = alias.replace(' ', '_')

    commandFile = "%s/command_%s.ps1" % (workFolder, alias)
    with open(commandFile, 'w') as fd:
        fd.write("""\nWrite-Host \"starting...\"\n\nWrite-Host \"PATH is:$PATH\"\n\n""")
        fd.write(commands)

    command = "powershell -File \"%s\" 2>&1 > %s/command_%s.log" % (commandFile, workFolder, alias)

    retval = call(command, shell=True)

    if DEBUG:
        print(("  external command %s exit code:%s" % (alias, retval)))

    if retval != 0:
        raise Exception("External command %s error:%s" % (alias, retval))

    print(("  external %s exit code:%s" % (alias, retval)))

    return retval
