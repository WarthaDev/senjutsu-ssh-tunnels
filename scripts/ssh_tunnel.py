import atexit
import re
import shlex
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Union
from gradio import strings
import os, requests, stat

from modules.shared import cmd_opts

# Fungsi untuk menghentikan tunnel
def kill_tunnel(proc):
    if proc is not None:
        proc.terminate()

# Fungsi untuk menghasilkan kunci SSH
def gen_ssh_key(path: Union[str, Path]) -> None:
    path = Path(path)
    arg_string = f'ssh-keygen -t rsa -b 4096 -N "" -q -f {path.as_posix()}'
    args = shlex.split(arg_string)
    subprocess.run(args, check=True)
    path.chmod(0o600)

# Fungsi untuk membuat SSH tunnel ke host
def create_ssh_tunnel(host: str, port: int, ssh_path: Path) -> str:
    arg_string = f"ssh -R 80:127.0.0.1:{port} -o StrictHostKeyChecking=no -i {ssh_path.as_posix()} {host}"
    args = shlex.split(arg_string)

    tunnel = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8")

    atexit.register(kill_tunnel, tunnel)

    tunnel_url = ""
    pattern = re.compile(r"(?P<url>https?://\S+\.\S+)")

    while not tunnel_url:
        line = tunnel.stdout.readline()
        if line.startswith("Warning"):
            print(line, end="")
        url_match = pattern.search(line)
        if url_match:
            tunnel_url = url_match.group("url")
            break

    if not tunnel_url:
        raise RuntimeError(f"Failed to create tunnel for {host}")

    return tunnel_url

# Membuat kunci SSH jika belum ada
def generate_ssh_key(ssh_path: Path) -> None:
    if not ssh_path.exists():
        try:
            gen_ssh_key(ssh_path)
        except subprocess.CalledProcessError:
            tmp = TemporaryDirectory()
            ssh_path = Path(tmp.name) / ssh_path.name
            gen_ssh_key(ssh_path)
    ssh_path.chmod(0o600)

# Membuat SSH tunnel untuk localhost.run
def create_localhostrun_tunnel() -> str:
    print("Creating tunnel for localhost.run...")
    ssh_path = Path(__file__).parent.parent / "id_rsa"
    generate_ssh_key(ssh_path)
    return create_ssh_tunnel("localhost.run", 7860, ssh_path)

# Membuat SSH tunnel untuk remote.moe
def create_remotemoe_tunnel() -> str:
    print("Creating tunnel for remote.moe...")
    ssh_path = Path(__file__).parent.parent / "id_rsa"
    generate_ssh_key(ssh_path)
    return create_ssh_tunnel("remote.moe", 7860, ssh_path)

# Membuat SSH tunnel untuk googleusercontent.com
def create_googleusercontent_tunnel() -> str:
    print("Creating tunnel for googleusercontent.com...")
    colab_url = os.getenv('colab_url')
    return colab_url

# Main program
if cmd_opts.localhostrun:
    try:
        os.environ['LOCALHOST_RUN'] = create_localhostrun_tunnel()
    except Exception as e:
        print(f"Failed to create tunnel for localhost.run: {str(e)}")

if cmd_opts.remotemoe:
    try:
        os.environ['REMOTE_MOE'] = create_remotemoe_tunnel()
    except Exception as e:
        print(f"Failed to create tunnel for remote.moe: {str(e)}")

if cmd_opts.googleusercontent:
    try:
        os.environ['GOOGLEUSERCONTENT'] = create_googleusercontent_tunnel()
    except Exception as e:
        print(f"Failed to create tunnel for googleusercontent.com: {str(e)}")

if cmd_opts.multiple:
    try:
        os.environ['LOCALHOST_RUN'] = create_localhostrun_tunnel()
    except Exception as e:
        print(f"Failed to create tunnel for localhost.run: {str(e)}")

    try:
        os.environ['REMOTE_MOE'] = create_remotemoe_tunnel()
    except Exception as e:
        print(f"Failed to create tunnel for remote.moe: {str(e)}")

    try:
        os.environ['GOOGLEUSERCONTENT'] = create_googleusercontent_tunnel()
    except Exception as e:
        print(f"Failed to create tunnel for googleusercontent.com: {str(e)}")

strings.en["SHARE_LINK_MESSAGE"] = f"Wartha Sensei Public URL(localhost.run): {os.getenv('LOCALHOST_RUN')}\nPublic WebUI Colab URL (remote.moe): {os.getenv('REMOTE_MOE')}\nPublic WebUI Colab URL (googleusercontent.com): {os.getenv('GOOGLEUSERCONTENT')}"

