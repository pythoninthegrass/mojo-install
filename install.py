#!/usr/bin/env python3

import os
import platform
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

# TODO use shutil to copy files

ARCH = "x86_64-linux-gnu"


def param(name: str):
    try:
        return os.environ[name]
    except:
        return None


HOME = param("HOME")
if HOME is None:
    HOME = Path("~").expanduser()

WORK_DIR = f"{HOME}/.local/arch-mojo/"
PKGBUILD_URL = "https://raw.githubusercontent.com/Sharktheone/arch-mojo/main/PKGBUILD"
LIBINFO_URL = "https://ftp.debian.org/debian/pool/main/n/ncurses/libtinfo6_6.4-4_amd64.deb"
LIBNCURSES_URL = "https://ftp.debian.org/debian/pool/main/n/ncurses/libncurses6_6.4-4_amd64.deb"
LIBEDIT_URL = "https://ftp.debian.org/debian/pool/main/libe/libedit/libedit2_3.1-20221030-2_amd64.deb"
GLOBAL_INSTALL = False
ONLY_MOJO = False
FEDORA = False
SKIP_NEXT_ARG = False
TOKEN = None
MOJO_LIB_RELATIVE_PATH = ".local/lib/mojo"
MOJO_LIB_PATH = f"{HOME}/{MOJO_LIB_RELATIVE_PATH}"
modular = shutil.which("modular") is not None

authenticated = False
if modular:
    authenticated = "user.id" in subprocess.run(["modular", "config-list"],
                                                capture_output=True).stdout.decode("utf-8")

for arg in sys.argv:
    if SKIP_NEXT_ARG:
        SKIP_NEXT_ARG = False
        continue

    if arg.startswith("--dir="):
        WORK_DIR = arg.split("=")[1]
    elif arg.startswith("-d="):
        WORK_DIR = arg.split("=")[1]
    elif arg == "--global":
        GLOBAL_INSTALL = True
    elif arg == "-g":
        GLOBAL_INSTALL = True
    elif arg == "--mojo":
        ONLY_MOJO = True
    elif arg == "-m":
        ONLY_MOJO = True
    elif arg == "--fedora":
        FEDORA = True
    elif arg == "-f":
        FEDORA = True
    elif arg == "--modular-token":
        index = sys.argv.index(arg) + 1
        if index >= len(sys.argv):
            print("No token provided")
            exit(1)
        TOKEN = sys.argv[index]

        if TOKEN == "" or not TOKEN.startswith("mut_") or not len(TOKEN) == 36:
            print("Invalid token")
            exit(1)
        SKIP_NEXT_ARG = True
    elif arg == "--help" \
            or arg == "-h":
        print("Usage: python3 install.py [options]")
        print("Options:")
        print("  --dir=<path>  | -d=<path>  : Set the working directory")
        print("  --global      | -g         : Install the libs globally")
        print("  --help        | -h         : Show this help message")
        print("  --mojo        | -m         : Only install mojo (modular must be installed)")
        print("  --fedora      | -f         : Install for fedora")
        print("  --modular-token <token>    : Set the modular token")
        exit(0)

WORK_DIR = WORK_DIR.replace("~", param("HOME"))

if ONLY_MOJO and not modular:
    print("Modular must be installed to install mojo")
    exit(1)

try:
    os.makedirs(WORK_DIR)
except FileExistsError:
    pass

# install dependencies
if platform.system() == "Linux":
    os_release = subprocess.run(["cat", "/etc/*release"],
                                capture_output=True).stdout.decode("utf-8")
    # cat /etc/os-release | grep -E "^ID"
    # os_id =

if FEDORA:
    os.system("sudo dnf install -y binutils")

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
if not modular:
    # download PKGBUILD
    urllib.request.urlretrieve(PKGBUILD_URL,
                               f"{WORK_DIR}/PKGBUILD")
    os.system(f"cd {WORK_DIR}/ && makepkg -si")

# authenticate in modular
if not authenticated:
    if TOKEN is None and param("MODULAR_TOKEN") is not None:
        TOKEN = param("MODULAR_TOKEN")
    else:
        TOKEN = input("Please enter your Modular auth token: ")
    os.system(f"LD_LIBRARY_PATH=$LD_LIBRARY_PATH:{MOJO_LIB_PATH} modular auth {TOKEN}")

# download ncurses lib
urllib.request.urlretrieve(LIBNCURSES_URL,
                           f"{WORK_DIR}/libncurses.deb")

# download libedit lib
urllib.request.urlretrieve(LIBEDIT_URL,
                           f"{WORK_DIR}/libedit.deb")

os.system(f"cd {WORK_DIR}/ && ar -vx libncurses.deb && tar -xf data.tar.xz")
os.system(f"cd {WORK_DIR}/ && ar -vx libedit.deb && tar -xf data.tar.xz")


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
