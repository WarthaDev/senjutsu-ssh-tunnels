import atexit
import re
import shlex
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Union
import os
import requests
import stat

from modules.shared import cmd_opts
from gradio import strings

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

# Fungsi untuk mendapatkan Gradio tunnel URL
def get_gradio_tunnel_url() -> str:
    print("Getting Gradio tunnel URL...")
    return gradio_tunnel()

# Fungsi untuk menghentikan tunnel Gradio
def kill_gradio_tunnel():
    gradio_tunnel_url = os.getenv('GRADIO_TUNNEL')
    if gradio_tunnel_url:
        print("Killing Gradio tunnel...")
        subprocess.call(["frpc_linux_amd64", "http", "-c", "gradio.ini", "stop"])

# Fungsi untuk mendapatkan URL publik dari Gradio
def gradio_tunnel():
    script_path = os.path.dirname(os.path.abspath(__file__))
    binary_path = os.path.join(script_path, "frpc_linux_amd64")
    response = requests.get("https://api.gradio.app/v2/tunnel-request")
    if response and response.status_code == 200:
        try:
            payload = response.json()[0]
            remote_host, remote_port = payload["host"], int(payload["port"])
            resp = requests.get("https://cdn-media.huggingface.co/frpc-gradio-0.1/frpc_linux_amd64")
            with open(binary_path, "wb") as file:
                file.write(resp.content)
            st = os.stat(binary_path)
            os.chmod(binary_path, st.st_mode | stat.S_IEXEC)
            command = [
                binary_path, "http", "-n", "random", "-l", "7860", "-i", "127.0.0.1",
                "--uc", "--sd", "random", "--ue", "--server_addr", f"{remote_host}:{remote_port}",
                "--disable_log_color"
            ]
            proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            atexit.register(kill_gradio_tunnel)
            url = ""
            while url == "":
                if proc.stdout is None:
                    continue
                line = proc.stdout.readline()
                line = line.decode("utf-8")
                if "start proxy success" in line:
                    result = re.search("start proxy success: (.+)\n", line)
                    if result is None:
                        raise ValueError("Could not create share URL")
                    else:
                        url = result.group(1)
            return url
        except Exception as e:
            raise RuntimeError(str(e))
    else:
        raise RuntimeError("Could not get share link from Gradio API Server.")

# Mengatur opsi bahasa Gradio menjadi bahasa Inggris
strings.set_gradio_locale("en")

if cmd_opts.localhostrun:
    os.environ['LOCALHOST_RUN'] = create_localhostrun_tunnel()

if cmd_opts.remotemoe:
    os.environ['REMOTE_MOE'] = create_remotemoe_tunnel()

if cmd_opts.googleusercontent:
    os.environ['GOOGLEUSERCONTENT'] = create_googleusercontent_tunnel()

if cmd_opts.multiple:
    os.environ['GRADIO_TUNNEL'] = get_gradio_tunnel_url()

strings.en["SHARE_LINK_MESSAGE"] = "WebUI Colab URL: {}"

if cmd_opts.multiple:
    strings.en["RUNNING_LOCALLY_SEPARATED"] = "Public WebUI Colab URL: {}\nPublic WebUI Colab URL: {}\nPublic WebUI Colab URL: {}"
else:
    strings.en["SHARE_LINK_DISPLAY"] = "Please do not use this link, we are getting an ERROR: Exception in ASGI application: {}"
        
