from __future__ import annotations

import logging
import os
import platform
import shutil
import stat
import subprocess
from subprocess import DEVNULL
from subprocess import Popen
from subprocess import call
from time import sleep

import nzb2media

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def extract(file_path, output_destination):
    success = 0
    # Using Windows
    if platform.system() == 'Windows':
        if not os.path.exists(nzb2media.SEVENZIP):
            log.error('EXTRACTOR: Could not find 7-zip, Exiting')
            return False
        wscriptlocation = os.path.join(os.environ['WINDIR'], 'system32', 'wscript.exe')
        invislocation = os.path.join(nzb2media.APP_ROOT, 'nzb2media', 'extractor', 'bin', 'invisible.vbs')
        cmd_7zip = [wscriptlocation, invislocation, str(nzb2media.SHOWEXTRACT), nzb2media.SEVENZIP, 'x', '-y']
        ext_7zip = ['.rar', '.zip', '.tar.gz', 'tgz', '.tar.bz2', '.tbz', '.tar.lzma', '.tlz', '.7z', '.xz', '.gz']
        extract_commands = dict.fromkeys(ext_7zip, cmd_7zip)
    # Using unix
    else:
        required_cmds = ['unrar', 'unzip', 'tar', 'unxz', 'unlzma', '7zr', 'bunzip2', 'gunzip']
        # ## Possible future suport:
        # gunzip: gz (cmd will delete original archive)
        # ## the following do not extract to destination dir
        # '.xz': ['xz', '-d --keep'],
        # '.lzma': ['xz', '-d --format=lzma --keep'],
        # '.bz2': ['bzip2', '-d --keep']
        extract_commands = {'.rar': ['unrar', 'x', '-o+', '-y'], '.tar': ['tar', '-xf'], '.zip': ['unzip'], '.tar.gz': ['tar', '-xzf'], '.tgz': ['tar', '-xzf'], '.tar.bz2': ['tar', '-xjf'], '.tbz': ['tar', '-xjf'], '.tar.lzma': ['tar', '--lzma', '-xf'], '.tlz': ['tar', '--lzma', '-xf'], '.tar.xz': ['tar', '--xz', '-xf'], '.txz': ['tar', '--xz', '-xf'], '.7z': ['7zr', 'x'], '.gz': ['gunzip']}
        # Test command exists and if not, remove
        if not os.getenv('TR_TORRENT_DIR'):
            for cmd in required_cmds:
                if call(['which', cmd], stdout=DEVNULL, stderr=DEVNULL):
                    # note, returns 0 if exists, or 1 if doesn't exist.
                    for key, val in extract_commands.items():
                        if cmd in val[0]:
                            if not call(['which', '7zr'], stdout=DEVNULL, stderr=DEVNULL):
                                # we do have '7zr'
                                extract_commands[key] = ['7zr', 'x', '-y']
                            elif not call(['which', '7z'], stdout=DEVNULL, stderr=DEVNULL):
                                # we do have '7z'
                                extract_commands[key] = ['7z', 'x', '-y']
                            elif not call(['which', '7za'], stdout=DEVNULL, stderr=DEVNULL):
                                # we do have '7za'
                                extract_commands[key] = ['7za', 'x', '-y']
                            else:
                                log.error(f'EXTRACTOR: {cmd} not found, disabling support for {key}')
                                del extract_commands[key]
        else:
            log.warning('EXTRACTOR: Cannot determine which tool to use when called from Transmission')
        if not extract_commands:
            log.warning('EXTRACTOR: No archive extracting programs found, plugin will be disabled')
    ext = os.path.splitext(file_path)
    cmd = []
    if ext[1] in {'.gz', '.bz2', '.lzma'}:
        # Check if this is a tar
        if os.path.splitext(ext[0])[1] == '.tar':
            cmd = extract_commands[f'.tar{ext[1]}']
        else:  # Try gunzip
            cmd = extract_commands[ext[1]]
    elif ext[1] in {'.1', '.01', '.001'} and os.path.splitext(ext[0])[1] in {'.rar', '.zip', '.7z'}:
        cmd = extract_commands[os.path.splitext(ext[0])[1]]
    elif ext[1] in {'.cb7', '.cba', '.cbr', '.cbt', '.cbz'}:
        # don't extract these comic book archives.
        return False
    else:
        if ext[1] in extract_commands:
            cmd = extract_commands[ext[1]]
        else:
            log.debug(f'EXTRACTOR: Unknown file type: {ext[1]}')
            return False
        # Create outputDestination folder
        nzb2media.make_dir(output_destination)
    if nzb2media.PASSWORDS_FILE and os.path.isfile(os.path.normpath(nzb2media.PASSWORDS_FILE)):
        with open(os.path.normpath(nzb2media.PASSWORDS_FILE), encoding='utf-8') as fin:
            passwords = [line.strip() for line in fin]
    else:
        passwords = []
    log.info(f'Extracting {file_path} to {output_destination}')
    log.debug(f'Extracting {cmd} {file_path} {output_destination}')
    orig_files = []
    orig_dirs = []
    for directory, subdirs, files in os.walk(output_destination):
        for subdir in subdirs:
            orig_dirs.append(os.path.join(directory, subdir))
        for file in files:
            orig_files.append(os.path.join(directory, file))
    pwd = os.getcwd()  # Get our Present Working Directory
    # Not all unpack commands accept full paths, so just extract into this directory
    os.chdir(output_destination)
    try:  # now works same for nt and *nix
        info = None
        cmd.append(file_path)  # add filePath to final cmd arg.
        if platform.system() == 'Windows':
            info = subprocess.STARTUPINFO()
            info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        else:
            cmd = nzb2media.NICENESS + cmd
        cmd2 = cmd
        if 'gunzip' not in cmd:  # gunzip doesn't support password
            cmd2.append('-p-')  # don't prompt for password.
        with Popen(cmd2, stdout=DEVNULL, stderr=DEVNULL, startupinfo=info) as proc:
            res = proc.wait()  # should extract files fine.
        if not res:  # Both Linux and Windows return 0 for successful.
            log.info(f'EXTRACTOR: Extraction was successful for {file_path} to {output_destination}')
            success = 1
        elif len(passwords) > 0 and 'gunzip' not in cmd:
            log.info('EXTRACTOR: Attempting to extract with passwords')
            for password in passwords:
                if not password:
                    continue  # if edited in windows or otherwise if blank lines.
                cmd2 = cmd
                # append password here.
                passcmd = f'-p{password}'
                cmd2.append(passcmd)
                with Popen(cmd2, stdout=DEVNULL, stderr=DEVNULL, startupinfo=info) as proc:
                    res = proc.wait()  # should extract files fine.
                if not res or (res >= 0 and platform == 'Windows'):
                    log.info(f'EXTRACTOR: Extraction was successful for {file_path} to {output_destination} using password: {password}')
                    success = 1
                    break
    except Exception:
        log.error(f'EXTRACTOR: Extraction failed for {file_path}. Could not call command {cmd}')
        os.chdir(pwd)
        return False
    os.chdir(pwd)  # Go back to our Original Working Directory
    if success:
        # sleep to let files finish writing to disk
        sleep(3)
        perms = stat.S_IMODE(os.lstat(os.path.split(file_path)[0]).st_mode)
        for directory, subdirs, files in os.walk(output_destination):
            for subdir in subdirs:
                if not os.path.join(directory, subdir) in orig_files:
                    try:
                        os.chmod(os.path.join(directory, subdir), perms)
                    except Exception:
                        pass
            for file in files:
                if not os.path.join(directory, file) in orig_files:
                    try:
                        shutil.copymode(file_path, os.path.join(directory, file))
                    except Exception:
                        pass
        return True
    log.error(f'EXTRACTOR: Extraction failed for {file_path}. Result was {res}')
    return False
