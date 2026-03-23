#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${1:-$SCRIPT_DIR/open3d_env}"
REQ_FILE="$SCRIPT_DIR/requirements-lidar.txt"
TOOL_FILE="$SCRIPT_DIR/lidar_topography_tool.py"

run() {
  printf '+'
  for arg in "$@"; do
    printf ' %q' "$arg"
  done
  printf '\n'
  "$@"
}

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "Error: this installer is Linux-only." >&2
  exit 1
fi

if [[ ! -f "$REQ_FILE" ]]; then
  echo "Error: requirements file not found: $REQ_FILE" >&2
  exit 1
fi

if [[ ! -f "$TOOL_FILE" ]]; then
  echo "Error: main script not found: $TOOL_FILE" >&2
  exit 1
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Error: '$PYTHON_BIN' was not found. Install Python 3 first." >&2
  exit 1
fi

PYTHON_VERSION="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"

echo "Using Python: $PYTHON_BIN ($PYTHON_VERSION)"
case "$PYTHON_VERSION" in
  3.10|3.11|3.12) ;;
  *)
    echo "Warning: Python $PYTHON_VERSION may not have a compatible Open3D wheel."
    echo "Recommended versions are 3.10, 3.11, or 3.12."
    ;;
esac

if [[ ! -d "$VENV_DIR" ]]; then
  echo "Creating virtual environment at $VENV_DIR"
  run "$PYTHON_BIN" -m venv "$VENV_DIR"
else
  echo "Reusing existing virtual environment at $VENV_DIR"
fi

VENV_PY="$VENV_DIR/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
  echo "Error: virtual environment Python not found: $VENV_PY" >&2
  exit 1
fi

echo "Upgrading pip tooling..."
run "$VENV_PY" -m pip install --upgrade pip setuptools wheel

echo "Installing project dependencies..."
run "$VENV_PY" -m pip install --upgrade -r "$REQ_FILE"

echo "Verifying imports..."
run "$VENV_PY" -c 'import numpy, scipy, open3d; print("Installed successfully:"); print(f"  numpy  {numpy.__version__}"); print(f"  scipy  {scipy.__version__}"); print(f"  open3d {open3d.__version__}")'

echo
echo "Environment is ready."
echo "Activate it with:"
echo "  source \"$VENV_DIR/bin/activate\""
echo
echo "Run the tool with:"
echo "  \"$VENV_PY\" \"$TOOL_FILE\""
