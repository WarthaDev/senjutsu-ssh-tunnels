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
from gradio import strings

from modules.shared import cmd_opts

LOCALHOST_RUN = "localhost.run"
REMOTE_MOE = "remote.moe"
GOOGLE_USER_CONTENT = "googleusercontent.com"
localhostrun_pattern = re.compile(r"(?P<url>https?://\S+\.lhr\.life)")
remotemoe_pattern = re.compile(r"(?P<url>https?://\S+\.remote\.moe)")

def kill_tunnel(proc):
    if proc is not None:
        print(f"Menutup tunnel 127.0.0.1:7860")
        proc.terminate()

def gradio_tunnel() -> str:
    # Kode implementasi gradio_tunnel
    # ...

def ssh_tunnel(host: str) -> str:
    # Kode implementasi ssh_tunnel
    # ...

def google_tunnel() -> str:
    colab_url = os.getenv('colab_url')
    return colab_url

def get_public_urls() -> list[str]:
    public_urls = []
    if cmd_opts.localhostrun:
        print("localhost.run terdeteksi, mencoba terhubung...")
        public_urls.append(ssh_tunnel(LOCALHOST_RUN))

    if cmd_opts.remotemoe:
        print("remote.moe terdeteksi, mencoba terhubung...")
        public_urls.append(ssh_tunnel(REMOTE_MOE))

    if cmd_opts.googleusercontent:
        print("googleusercontent.com terdeteksi, mencoba terhubung...")
        public_urls.append(google_tunnel())

    if cmd_opts.multiple:
        print("Semua terdeteksi, mencoba terhubung...")
        try:
            public_urls.append(ssh_tunnel(LOCALHOST_RUN))
        except:
            pass

        try:
            public_urls.append(ssh_tunnel(REMOTE_MOE))
        except:
            pass

        try:
            public_urls.append(gradio_tunnel())
        except:
            pass

        try:
            public_urls.append(google_tunnel())
        except:
            pass

        try:
            public_urls.append(ssh_tunnel(LOCALHOST_RUN))
        except:
            pass

    return public_urls[:5]  # Ambil 5 URL publik pertama

public_urls = get_public_urls()

strings.en["RUNNING_LOCALLY_SEPARATED"] = "\n".join(f"Public URL {i+1}: {url}" for i, url in enumerate(public_urls))

# ...
