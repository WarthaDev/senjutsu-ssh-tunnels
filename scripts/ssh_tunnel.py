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

#...

def ssh_tunnel(host: str) -> str:
    #...
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
        raise RuntimeError(f"Failed to run {host}")

    return tunnel_url

def googleusercontent_tunnel():
    colab_url = os.getenv('colab_url')
    if colab_url:
        strings.en["SHARE_LINK_MESSAGE"] = f"Public URL: {colab_url}"

share_link_messages = []

if cmd_opts.gradio:
    print("Gradio terdeteksi, mencoba menghubungkan...")
    try:
        gradio_tunnel_url = gradio_tunnel()
        share_link_messages.append(f"Public Gradio URL: {gradio_tunnel_url}")
        share_link_messages.append(f"Public Gradio URL: {gradio_tunnel_url}")
    except:
        pass

if cmd_opts.localhostrun:
    print("localhost.run terdeteksi, mencoba menghubungkan...")
    tunnel_url = ssh_tunnel(LOCALHOST_RUN)
    share_link_messages.append(f"Public localhost.run URL: {tunnel_url}")

if cmd_opts.remotemoe:
    print("remote.moe terdeteksi, mencoba menghubungkan...")
    tunnel_url = ssh_tunnel(REMOTE_MOE)
    share_link_messages.append(f"Public remote.moe URL: {tunnel_url}")

if cmd_opts.googleusercontent:
    print("googleusercontent.com terdeteksi, mencoba menghubungkan...")
    googleusercontent_tunnel()

if cmd_opts.multiple:
    print("Semua terdeteksi, mencoba menghubungkan remote.moe...")
    try:
        tunnel_url = ssh_tunnel(LOCALHOST_RUN)
        share_link_messages.append(f"Public localhost.run URL: {tunnel_url}")
    except:
        pass
    try:
        tunnel_url = ssh_tunnel(REMOTE_MOE)
        share_link_messages.append(f"Public remote.moe URL: {tunnel_url}")
    except:
        pass

strings.en["SHARE_LINK_MESSAGE"] = "\n".join(share_link_messages)
    
