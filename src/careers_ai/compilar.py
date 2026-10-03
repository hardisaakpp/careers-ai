"""Compila el .tex a PDF con latexmk dentro de Docker Engine: sin instalar TeX en el equipo."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

IMAGEN_LATEX = os.environ.get("CAREERS_AI_LATEX_IMAGE", "ghcr.io/xu-cheng/texlive-alpine:latest")


def compilar(tex: Path) -> Path:
    env = {**os.environ, "DOCKER_CONTEXT": os.environ.get("CAREERS_AI_DOCKER_CONTEXT", "default")}
    subprocess.run(
        ["docker", "run", "--rm", "--network", "none", "--user", f"{os.getuid()}:{os.getgid()}",
         "-v", f"{tex.parent.resolve()}:/work", "-w", "/work", IMAGEN_LATEX,
         "latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "-no-shell-escape", tex.name],
        check=True, env=env, capture_output=True, timeout=120,
    )
    return tex.with_suffix(".pdf")
