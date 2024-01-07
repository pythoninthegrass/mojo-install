#!/usr/bin/env python3

import os
import platform
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path


# get os id
if platform.system() == "Linux":
    release_files = Path("/etc").glob("*release")
    os_release = []
    for file in release_files:
        os_release += file.read_text().splitlines()
    os_id = list(filter(lambda line: line.startswith("ID="), os_release))[0].split("=")[1].strip("\"")


class SysCall:
    @staticmethod
    def run_command(cmd: str, *args, capture_output: bool = False):
        """Run a system command"""
        if capture_output:
            result = subprocess.run(cmd, *args, shell=True, capture_output=True)
            return result
        else:
            if isinstance(cmd, list):
                cmd = ' '.join(cmd)
            return os.system(cmd, *args)

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
        cmd = f"cd {WORK_DIR} && ar -vx {path} && tar -xf {name} 2>&1 >/dev/null"   # TODO: still not working ('x - debian-binary')
        ret_code = SysCall.run_command(cmd)
        return True if ret_code == 0 else False

    @staticmethod
    def param(name: str):
        """Get an environment variable"""
        try:
            return os.environ.get(name)
        except KeyError:
            return None


# instantiate syscall class
syscall = SysCall()

# TODO: qa
# declare variables for each class method without any arguments
run_cmd = syscall.run_command
test_bin = syscall.test_bin
extract_deb = syscall.extract_deb
param = syscall.param

# fix crashdb directory not found
crashdb_dir = Path("/opt/modular/crashdb")
subprocess.run(['sudo', 'mkdir', '-p', f"{crashdb_dir}"])
subprocess.run(['sudo', 'chmod', '777', f"{crashdb_dir}"])

# check if modular is installed
modular = test_bin("modular")

# env vars
HOME = param("HOME")
if HOME is None:
    HOME = Path("~").expanduser()
TOKEN = None
ARCH = "x86_64-linux-gnu"
WORK_DIR = "/tmp/mojo-install"
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
    output = run_cmd(["modular", "config-list"], capture_output=True).stdout.decode("utf-8")
    if output != "":
        authenticated = "user.id" in output.splitlines()

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
    run_cmd(["sudo", cmd] + packages)

# TODO: qa
if not modular and os_id == "fedora":
    if not Path(f"{WORK_DIR}/libtinfo.deb").exists():
        urllib.request.urlretrieve(LIBINFO_URL,
                                f"{WORK_DIR}/libtinfo.deb")
        extract_deb("data.tar.xz", "libtinfo.deb")
    if GLOBAL_INSTALL:
        run_cmd(["sudo", "cp", str(Path(WORK_DIR) / f"lib/{ARCH}/libtinfo.so.6.4"), "/usr/lib/"])
        run_cmd(["sudo", "ln", "-sf", "/usr/lib/libtinfo.so.6.4", "/usr/lib/libtinfo.so.6"])
    else:
        mojo_lib_path = Path(MOJO_LIB_PATH)
        mojo_lib_path.mkdir(parents=True, exist_ok=True)
        run_cmd(["sudo", "cp", str(Path(WORK_DIR) / f"lib/{ARCH}/libtinfo.so.6.4"), str(mojo_lib_path / "libtinfo.so.6")])

# install modular if not installed
if not modular and os_id == "arch":
    if not Path(f"{WORK_DIR}/PKGBUILD").exists():
        urllib.request.urlretrieve(PKGBUILD_URL,
                                f"{WORK_DIR}/PKGBUILD")
    subprocess.run(["makepkg", "-si"], cwd=WORK_DIR)

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
    subprocess.run(["modular", "auth", TOKEN],
                    env={"LD_LIBRARY_PATH": f"{os.environ.get('LD_LIBRARY_PATH')}:{MOJO_LIB_PATH}"})

# download ncurses lib
urllib.request.urlretrieve(LIBNCURSES_URL,
                           f"{WORK_DIR}/libncurses.deb")

# download libedit lib
urllib.request.urlretrieve(LIBEDIT_URL,
                           f"{WORK_DIR}/libedit.deb")

extract_deb(f"{WORK_DIR}/libncurses.deb", "data.tar.xz")
extract_deb(f"{WORK_DIR}/libedit.deb", "data.tar.xz")


# TODO: qa
# copy libs
if GLOBAL_INSTALL:
    if GLOBAL_INSTALL:
        shutil.copy(f"{WORK_DIR}/lib/{ARCH}/libncurses.so.6.4", "/lib/libncurses.so.6.4")
        shutil.copy(f"{WORK_DIR}/usr/lib/{ARCH}/libform.so.6.4", "/usr/lib/libform.so.6.4")
        shutil.copy(f"{WORK_DIR}/usr/lib/{ARCH}/libpanel.so.6.4", "/usr/lib/libpanel.so.6.4")
        shutil.copy(f"{WORK_DIR}/usr/lib/{ARCH}/libedit.so.2.0.70", "/usr/lib/libedit.so.2.0.70")
        os.symlink("/lib/libncurses.so.6.4", "/lib/libncurses.so.6")
        os.symlink("/usr/lib/libform.so.6.4", "/usr/lib/libform.so.6")
        os.symlink("/usr/lib/libpanel.so.6.4", "/usr/lib/libpanel.so.6")
        os.symlink("/usr/lib/libedit.so.2.0.70", "/usr/lib/libedit.so.2")
    else:
        mojo_lib_path = Path(MOJO_LIB_PATH)
        mojo_lib_path.mkdir(parents=True, exist_ok=True)
        shutil.copy(f"{WORK_DIR}/lib/{ARCH}/libncurses.so.6.4", mojo_lib_path / "libncurses.so.6")
        shutil.copy(f"{WORK_DIR}/usr/lib/{ARCH}/libform.so.6.4", mojo_lib_path / "libform.so.6")
        shutil.copy(f"{WORK_DIR}/usr/lib/{ARCH}/libpanel.so.6.4", mojo_lib_path / "libpanel.so.6")
        shutil.copy(f"{WORK_DIR}/usr/lib/{ARCH}/libedit.so.2.0.70", mojo_lib_path / "libedit.so.2")

# install mojo
mojo = test_bin("mojo")
if mojo:
    print("Mojo is already installed... cleaning up")
    run_cmd("modular clean")

run_cmd(["modular", "install", "mojo"],
        env={"LD_LIBRARY_PATH": f"{os.environ.get('LD_LIBRARY_PATH')}:{MOJO_LIB_PATH}"})


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
