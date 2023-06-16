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

# ...

LOCALHOST_RUN = "localhost.run"
REMOTE_MOE = "remote.moe"
localhostrun_pattern = re.compile(r"(?P<url>https?://\S+\.lhr\.life)")
remotemoe_pattern = re.compile(r"(?P<url>https?://\S+\.remote\.moe)")

# ...

def remote_moe_tunnel():
    ssh_name = "id_rsa"
    ssh_path = Path(__file__).parent.parent / ssh_name

    tmp = None
    if not ssh_path.exists():
        try:
            gen_key(ssh_path)
        except subprocess.CalledProcessError:
            tmp = TemporaryDirectory()
            ssh_path = Path(tmp.name) / ssh_name
            gen_key(ssh_path)

    port = cmd_opts.port if cmd_opts.port else 7860

    arg_string = f"ssh -R 80:127.0.0.1:{port} -o StrictHostKeyChecking=no -i {ssh_path.as_posix()} {REMOTE_MOE}"
    args = shlex.split(arg_string)

    tunnel = subprocess.Popen(
        args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8"
    )

    atexit.register(tunnel.terminate)
    if tmp is not None:
        atexit.register(tmp.cleanup)

    tunnel_url = ""
    lines = 5
    pattern = remotemoe_pattern

    for _ in range(lines):
        line = tunnel.stdout.readline()
        if line.startswith("Warning"):
            print(line, end="")

        url_match = pattern.search(line)
        if url_match:
            tunnel_url = url_match.group("url")
            os.environ['REMOTE_MOE'] = tunnel_url
            break
    else:
        raise RuntimeError(f"Failed to run {REMOTE_MOE}")

    strings.en["SHARE_LINK_MESSAGE"] = f"Public nama URL: {tunnel_url}"

# ...

if cmd_opts.localhostrun:
    print("localhost.run detected, trying to connect...")
    ssh_tunnel(LOCALHOST_RUN)

if cmd_opts.remotemoe:
    print("remote.moe detected, trying to connect...")
    remote_moe_tunnel()

if cmd_opts.googleusercontent:
    print("googleusercontent.com detected, trying to connect...")
    googleusercontent_tunnel()

if cmd_opts.multiple:
    print("all detected, remote.moe trying to connect...")
    try:
        ssh_tunnel(LOCALHOST_RUN)
    except:
        pass
    try:
        remote_moe_tunnel()
    except:
        pass
    try:
        os.environ['GRADIO_TUNNEL'] = gradio_tunnel()
    except:
        pass
    strings.en["RUNNING_LOCALLY_SEPARATED"] = f"Public nama URL: {os.getenv('REMOTE_MOE')} \nPublic nama URL: {os.getenv('GRADIO_TUNNEL')} \nPublic nama URL: {os.getenv('LOCALHOST_RUN')}"
    strings.en["SHARE_LINK_DISPLAY"] = "Please do not use this link we are getting ERROR: Exception in ASGI application:  {}"
            
