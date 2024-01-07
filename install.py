#!/usr/bin/env python3

import os
import platform
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

# TODO use shutil to copy files

class SysCall:
    @staticmethod
    def run_command(cmd: str):
        """Run a system command"""
        return os.system(cmd)

    @staticmethod
    def test_bin(name: str):
        """Check if bin is installed"""
        if os_id == "arch":
            cmd = f"pacman -Qs {name} 2>&1 >/dev/null"
        elif os_id == "fedora":
            cmd = f"rpm -q {name} 2>&1 >/dev/null"
        ret_code = SysCall.run_command(cmd)
        return True if shutil.which(name) is not None or ret_code == 0 else False

    @staticmethod
    def extract_deb(name: str, path: str):
        """Extract a deb file"""
        cmd = f"cd {WORK_DIR} && ar -vx {path} && tar -xf {name}"
        ret_code = SysCall.run_command(cmd)
        return True if ret_code == 0 else False


def param(name: str):
    """Get an environment variable"""
    try:
        return os.environ.get(name)
    except KeyError:
        return None


# get os id
if platform.system() == "Linux":
    release_files = Path("/etc").glob("*release")
    os_release = []
    for file in release_files:
        os_release += file.read_text().splitlines()
    os_id = list(filter(lambda line: line.startswith("ID="), os_release))[0].split("=")[1].strip("\"")


def test_bin(name: str):
    """Check if bin is installed"""
    if os_id == "arch":
        cmd = f"pacman -Qs {name} 2>&1 >/dev/null"
    elif os_id == "fedora":
        cmd = f"rpm -q {name} 2>&1 >/dev/null"
        ret_code = os.system(cmd)
    return True if shutil.which(name) is not None or ret_code == 0 else False


def extract_deb(name: str, path: str):
    """Extract a deb file"""
    ret_code = os.system(f"cd {WORK_DIR} && ar -vx {path} && tar -xf {name}")
    return True if ret_code == 0 else False


# check if modular is installed
modular = test_bin("modular")

# instantiate syscall class
syscall = SysCall()

# declare variables for each class method without any arguments
run_command = syscall.run_command
test_bin = syscall.test_bin
extract_deb = syscall.extract_deb

# env vars
HOME = param("HOME")
if HOME is None:
    HOME = Path("~").expanduser()
TOKEN = None
ARCH = "x86_64-linux-gnu"
WORK_DIR = f"{HOME}/.local/arch-mojo/"
PKGBUILD_URL = "https://raw.githubusercontent.com/Sharktheone/arch-mojo/main/PKGBUILD"
LIBINFO_URL = "https://ftp.debian.org/debian/pool/main/n/ncurses/libtinfo6_6.4-4_amd64.deb"
LIBNCURSES_URL = "https://ftp.debian.org/debian/pool/main/n/ncurses/libncurses6_6.4-4_amd64.deb"
LIBEDIT_URL = "https://ftp.debian.org/debian/pool/main/libe/libedit/libedit2_3.1-20221030-2_amd64.deb"
GLOBAL_INSTALL = False
ONLY_MOJO = False
SKIP_NEXT_ARG = False
MOJO_LIB_RELATIVE_PATH = ".local/lib/mojo"
MOJO_LIB_PATH = f"{HOME}/{MOJO_LIB_RELATIVE_PATH}"

authenticated = False
if modular:
    authenticated = "user.id" in subprocess.run(["modular", "config-list"],
                                                capture_output=True).stdout.decode("utf-8")

skip_next_arg = SKIP_NEXT_ARG
for i in range(1, len(sys.argv)):
    arg = sys.argv[i]
    if skip_next_arg:
        skip_next_arg = False
        continue

    match arg:
        case "--dir" | "-d":
            if i+1 >= len(sys.argv):
                print("No directory provided")
                exit(1)
            WORK_DIR = sys.argv[i+1]
            skip_next_arg = True
        case "--global" | "-g":
            GLOBAL_INSTALL = True
        case "--mojo" | "-m":
            ONLY_MOJO = True
        case "--modular-token":
            if i+1 >= len(sys.argv):
                print("No token provided")
                exit(1)
            TOKEN = sys.argv[i+1]
            if TOKEN == "" or not TOKEN.startswith("mut_") or not len(TOKEN) == 36:
                print("Invalid token")
                exit(1)
            skip_next_arg = True
        case "--help" | "-h":
            print("Usage: python3 install.py [options]")
            print("Options:")
            print("  --dir <path>  | -d <path>  : Set the working directory")
            print("  --global      | -g         : Install the libs globally")
            print("  --help        | -h         : Show this help message")
            print("  --mojo        | -m         : Only install mojo (modular must be installed)")
            print("  --fedora      | -f         : Install for fedora")
            print("  --modular-token <token>    : Set the modular token")
            exit(0)

WORK_DIR = WORK_DIR.replace("~", HOME)
Path(WORK_DIR).mkdir(parents=True, exist_ok=True)

if ONLY_MOJO and not modular:
    print("Modular must be installed to install mojo")
    exit(1)

# TODO: qa
# install dependencies
if os_id == "arch":
    deps = ["base-devel", "git", "binutils", "libbsd"]
    cmd = "pacman -S --noconfirm"
elif os_id == "fedora":
    deps = ["binutils"]
    cmd = "dnf install -y"

packages = []

for dep in deps:
    if test_bin(dep) is None:
        packages.append(dep)

if len(packages) > 0:
    os.system(f"sudo {cmd} {' '.join(packages)}")

if os_id == "fedora":
    urllib.request.urlretrieve(LIBINFO_URL,
                               f"{WORK_DIR}/libtinfo.deb")
    os.system(f"cd {WORK_DIR}/ && ar -vx libtinfo.deb && tar -xf data.tar.xz")
    if GLOBAL_INSTALL:
        os.system(f"sudo cp {WORK_DIR}/lib/{ARCH}/libtinfo.so.6.4 /usr/lib/")
        os.system("sudo ln -s /usr/lib/libtinfo.so.6.4 /usr/lib/libtinfo.so.6")
    else:
        os.system(f"mkdir -p {MOJO_LIB_PATH}")
        os.system(f"cp {WORK_DIR}/lib/{ARCH}/libtinfo.so.6.4 {MOJO_LIB_PATH}/libtinfo.so.6")

# install modular if not installed
if not modular and os_id == "arch":
    urllib.request.urlretrieve(PKGBUILD_URL,
                               f"{WORK_DIR}/PKGBUILD")
    os.system(f"cd {WORK_DIR}/ && makepkg -si")

# authenticate in modular
if not authenticated:
    if TOKEN is None and param("AUTH_KEY") is not None:
        TOKEN = param("AUTH_KEY")
    elif TOKEN is None and Path(".env").exists():
        with open(".env", "r") as env_file:
            for line in env_file.readlines():
                if line.startswith("AUTH_KEY="):
                    TOKEN = line.split("=")[1].strip()
                    break
    else:
        TOKEN = input("Please enter your Modular auth token: ")
    os.system(f"LD_LIBRARY_PATH=$LD_LIBRARY_PATH:{MOJO_LIB_PATH} modular auth {TOKEN}")

# download ncurses lib
urllib.request.urlretrieve(LIBNCURSES_URL,
                           f"{WORK_DIR}/libncurses.deb")

# download libedit lib
urllib.request.urlretrieve(LIBEDIT_URL,
                           f"{WORK_DIR}/libedit.deb")

os.system(f"cd {WORK_DIR} && ar -vx libncurses.deb && tar -xf data.tar.xz 2>&1 >/dev/null")
os.system(f"cd {WORK_DIR} && ar -vx libedit.deb && tar -xf data.tar.xz 2>&1 >/dev/null")


# copy libs
if GLOBAL_INSTALL:
    os.system(f"sudo cp {WORK_DIR}/lib/{ARCH}/libncurses.so.6.4 /lib/libncurses.so.6.4")
    os.system(f"sudo cp {WORK_DIR}/usr/lib/{ARCH}/libform.so.6.4 /usr/lib/libform.so.6.4")
    os.system(f"sudo cp {WORK_DIR}/usr/lib/{ARCH}/libpanel.so.6.4 /usr/lib/libpanel.so.6.4")
    os.system(f"sudo cp {WORK_DIR}/usr/lib/{ARCH}/libedit.so.2.0.70 /usr/lib/libedit.so.2.0.70")
    os.system("sudo ln -s /lib/libncurses.so.6.4 /lib/libncurses.so.6")
    os.system("sudo ln -s /usr/lib/libform.so.6.4 /usr/lib/libform.so.6")
    os.system("sudo ln -s /usr/lib/libpanel.so.6.4 /usr/lib/libpanel.so.6")
    os.system("sudo ln -s /usr/lib/libedit.so.2.0.70 /usr/lib/libedit.so.2")
else:
    os.system(f"mkdir -p {MOJO_LIB_PATH}")
    os.system(f"cp {WORK_DIR}/lib/{ARCH}/libncurses.so.6.4 {MOJO_LIB_PATH}/libncurses.so.6")
    os.system(f"cp {WORK_DIR}/usr/lib/{ARCH}/libform.so.6.4 {MOJO_LIB_PATH}/libform.so.6")
    os.system(f"cp {WORK_DIR}/usr/lib/{ARCH}/libpanel.so.6.4 {MOJO_LIB_PATH}/libpanel.so.6")
    os.system(f"cp {WORK_DIR}/usr/lib/{ARCH}/libedit.so.2.0.70 {MOJO_LIB_PATH}/libedit.so.2")

# install mojo
mojo = shutil.which(f"PATH=$PATH:{HOME}/.modular/pkg/packages.modular.com_mojo/bin/ mojo") is not None
if mojo:
    print("Mojo is already installed... cleaning up")
    os.system(f"PATH=$PATH:{HOME}/.modular/pkg/packages.modular.com_mojo/bin/ modular clean")

os.system(f"LD_LIBRARY_PATH=$LD_LIBRARY_PATH:{MOJO_LIB_PATH} modular install mojo")

# fix crashdb directory not found:
os.makedirs(f"{HOME}/.modular/crashdb", exist_ok=True)


def rc_path():
    match param("SHELL").split("/")[-1]:
        case "bash":
            return f"{param('HOME')}/.bashrc"
        case "zsh":
            return f"{param('HOME')}/.zshrc"
        case _:
            path = input("Please enter the path to your shell rc file (e.g., ~/.bashrc) or press ENTER to skip:")
            if path == "":
                return None
            return path.replace("~", param("HOME"))


rc_pth = rc_path()

if rc_pth is None:
    print("Skipping rc file installation")
    exit(0)

rc_file = open(rc_pth, "a")
shell_rc = open(rc_pth, "r").read()

# check if exports are already in rc file
if param("LD_LIBRARY_PATH") is None or \
        f"~/{MOJO_LIB_RELATIVE_PATH}" not in param("LD_LIBRARY_PATH") \
        or MOJO_LIB_PATH not in param("LD_LIBRARY_PATH"):
    rc_file.write(f"export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:~/{MOJO_LIB_RELATIVE_PATH}\n")

if param("PATH") is None \
        or "~/.modular/pkg/packages.modular.com_mojo/bin/" not in param("PATH") \
        or f"{HOME}.modular/pkg/packages.modular.com_mojo/bin/" not in param("PATH"):
    rc_file.write("export PATH=$PATH:~/.modular/pkg/packages.modular.com_mojo/bin/\n")
rc_file.close()

print(f"Please restart your shell or run `source {rc_pth}` to complete the installation")
