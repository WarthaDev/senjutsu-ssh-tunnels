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
        print("Menghentikan tunnel 127.0.0.1:7860")
        proc.terminate()

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
            command = [binary_path, "http", "-n", "random", "-l", "7860", "-i", "127.0.0.1", "--uc", "--sd", "random", "--ue", "--server_addr", f"{remote_host}:{remote_port}", "--disable_log_color"]
            proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            atexit.register(kill_tunnel, proc)
            url = ""
            while url == "":
                if proc.stdout is None:
                    continue
                line = proc.stdout.readline()
                line = line.decode("utf-8")
                if "start proxy success" in line:
                    result = re.search("start proxy success: (.+)\n", line)
                    if result is None:
                        raise ValueError("Tidak dapat membuat URL berbagi")
                    else:
                        url = result.group(1)
            return url
        except Exception as e:
            raise RuntimeError(str(e))
    else:
        raise RuntimeError("Tidak dapat mendapatkan tautan berbagi dari Gradio API Server.")

LOCALHOST_RUN = "localhost.run"
REMOTE_MOE = "remote.moe"
localhostrun_pattern = re.compile(r"(?P<url>https?://\S+\.lhr\.life)")
remotemoe_pattern = re.compile(r"(?P<url>https?://\S+\.remote\.moe)")


def gen_key(path: Union[str, Path]) -> None:
    path = Path(path)
    arg_string = f'ssh-keygen -t rsa -b 4096 -N "" -q -f {path.as_posix()}'
    args = shlex.split(arg_string)
    subprocess.run(args, check=True)
    path.chmod(0o600)


def ssh_tunnel(host: str = LOCALHOST_RUN) -> None:
    ssh_name = "id_rsa"
    ssh_path = Path(__file__).parent.parent / ssh_name

    tmp = None
    if not ssh_path.exists():
        try:
            gen_key(ssh_path)
        # write permission error or etc
        except subprocess.CalledProcessError:
            tmp = TemporaryDirectory()
            ssh_path = Path(tmp.name) / ssh_name
            gen_key(ssh_path)

    port = cmd_opts.port if cmd_opts.port else 7860

    arg_string = f"ssh -R 80:127.0.0.1:{port} -o StrictHostKeyChecking=no -i {ssh_path.as_posix()} {host}"
    args = shlex.split(arg_string)

    tunnel = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8")

    atexit.register(kill_tunnel, tunnel)
    if tmp is not None:
        atexit.register(tmp.cleanup)

    tunnel_url = ""
    lines = 27 if host == LOCALHOST_RUN else 5
    pattern = localhostrun_pattern if host == LOCALHOST_RUN else remotemoe_pattern

    for _ in range(lines):
        line = tunnel.stdout.readline()
        if line.startswith("Warning"):
            print(line, end="")

        url_match = pattern.search(line)
        if url_match:
            tunnel_url = url_match.group("url")
            if lines == 27:
                os.environ['LOCALHOST_RUN'] = tunnel_url
            else:
                os.environ['REMOTE_MOE'] = tunnel_url
            break
    else:
        raise RuntimeError(f"Gagal menjalankan {host}")

    if not cmd_opts.multiple:
        strings.en["SHARE_LINK_MESSAGE"] = f"URL WebUI Publik Colab: [{tunnel_url}](https://{tunnel_url})"

def googleusercontent_tunnel():
    colab_url = os.getenv('colab_url')
    strings.en["SHARE_LINK_MESSAGE"] = f"URL WebUI Colab: [{colab_url}](https://{colab_url})"

if cmd_opts.localhostrun:
    print("localhost.run terdeteksi, mencoba menghubungkan...")
    ssh_tunnel(LOCALHOST_RUN)
    
if cmd_opts.remotemoe:
    print("remote.moe terdeteksi, mencoba menghubungkan...")
    ssh_tunnel(REMOTE_MOE)

if cmd_opts.googleusercontent:
    print("googleusercontent.com terdeteksi, mencoba menghubungkan...")
    googleusercontent_tunnel()

if cmd_opts.multiple:
    print("Semua terdeteksi, mencoba menghubungkan ke remote.moe...")
    try:
        ssh_tunnel(LOCALHOST_RUN)
    except:
        pass
      
    try:
        ssh_tunnel(REMOTE_MOE)
    except:
        pass

    try:
        os.environ['GRADIO_TUNNEL'] = gradio_tunnel()
    except:
        pass

    running_locally_separated = "\nPublic URL: https://{}\nPublic URL: https://{}\nPublic URL: https://{}".format(
        os.getenv('REMOTE_MOE'),
        os.getenv('GRADIO_TUNNEL'),
        os.getenv('LOCALHOST_RUN')
    )
    strings.en["RUNNING_LOCALLY_SEPARATED"] = running_locally_separated
    strings.en["SHARE_LINK_DISPLAY"] = "Harap jangan gunakan tautan ini, kami mendapatkan ERROR: Exception in ASGI application:  {}"
