#!/usr/bin/env bash
set -euo pipefail

PREFIX_DIR="${HOME}/.email2llm"
VENV_DIR="${PREFIX_DIR}/.venv"
BIN_DIR="${HOME}/.local/bin"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

say() { printf '%s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }

as_root() {
  if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
    "$@"
  elif have sudo; then
    sudo "$@"
  else
    say "error: need root privileges for: $*"
    exit 1
  fi
}

install_pandoc() {
  if have pandoc; then
    return
  fi

  case "$(uname -s)" in
    Darwin)
      if ! have brew; then
        say "error: Homebrew is required to install Pandoc"
        exit 1
      fi
      brew install pandoc
      ;;
    Linux)
      if have apt-get; then
        as_root apt-get update
        as_root apt-get install -y pandoc python3 python3-venv
      elif have dnf; then
        as_root dnf install -y pandoc python3
      elif have yum; then
        as_root yum install -y pandoc python3
      elif have pacman; then
        as_root pacman -Sy --noconfirm pandoc python
      elif have apk; then
        as_root apk add --no-cache pandoc python3 py3-virtualenv
      else
        say "error: install Pandoc and Python 3, then rerun this installer"
        exit 1
      fi
      ;;
    *)
      say "error: unsupported operating system: $(uname -s)"
      exit 1
      ;;
  esac
}

main() {
  install_pandoc

  if ! have python3; then
    say "error: Python 3.10 or newer is required"
    exit 1
  fi
  if [[ ! -f "${SCRIPT_DIR}/pyproject.toml" || ! -d "${SCRIPT_DIR}/email2llm" ]]; then
    say "error: run install.sh from an email2llm repository checkout"
    exit 1
  fi

  say "Setting up ${VENV_DIR}..."
  mkdir -p "${PREFIX_DIR}" "${BIN_DIR}"
  python3 -m venv "${VENV_DIR}"
  "${VENV_DIR}/bin/python" -m pip install --upgrade pip >/dev/null
  "${VENV_DIR}/bin/pip" install --editable "${SCRIPT_DIR}"
  ln -sf "${VENV_DIR}/bin/email2llm" "${BIN_DIR}/email2llm"

  say "Installed: ${BIN_DIR}/email2llm"
  if [[ ":${PATH}:" != *":${BIN_DIR}:"* ]]; then
    say "Add this directory to PATH: export PATH=\"${BIN_DIR}:\$PATH\""
  fi
}

main "$@"
