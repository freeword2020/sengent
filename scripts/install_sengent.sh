#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="${BASH_SOURCE[0]}"
SCRIPT_DIR="$(cd -- "${SCRIPT_PATH%/*}" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

DEFAULT_OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://127.0.0.1:11434}"
DEFAULT_OLLAMA_MODEL="${OLLAMA_MODEL:-gemma4:e4b}"

PYTHON_BIN=""
VENV_DIR="${REPO_ROOT}/.venv"
WITH_PDF_BUILD=0
WITH_MAINTAINER_TOOLS=0
SKIP_OLLAMA=0
ENSURE_OLLAMA_MODEL=0
REFRESH_ACTIVE_SOURCES=0
DRY_RUN=0
OLLAMA_BASE_URL="${DEFAULT_OLLAMA_BASE_URL}"
OLLAMA_MODEL="${DEFAULT_OLLAMA_MODEL}"

usage() {
  cat <<EOF
Usage: scripts/install_sengent.sh [options]

Install Sengent from the current git checkout into a local virtualenv.

Typical modes:
  Runtime host:    scripts/install_sengent.sh --ensure-ollama-model
  Build-only host: scripts/install_sengent.sh --skip-ollama
  Maintainer host: scripts/install_sengent.sh --with-maintainer-tools --skip-ollama

Options:
  --python <path>            Python interpreter to use (default: python3.11, then python3)
  --venv-dir <path>          Virtualenv directory (default: .venv under repo root)
  --with-pdf-build           Install optional PDF build support (docling extra)
  --with-maintainer-tools    Install maintainer tools (docling + pytest)
  --skip-ollama              Skip Ollama notes and optional model handling
  --ensure-ollama-model      If ollama CLI exists, run 'ollama pull' for the target model
  --refresh-active-sources   Overwrite active source packs with the repo seed bundle
  --ollama-base-url <url>    Ollama HTTP API base URL (default: ${DEFAULT_OLLAMA_BASE_URL})
  --ollama-model <model>     Ollama model id (default: ${DEFAULT_OLLAMA_MODEL})
  --dry-run                  Print planned actions without executing them
  --help                     Show this help text
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --python)
      PYTHON_BIN="${2:?missing value for --python}"
      shift 2
      ;;
    --venv-dir)
      VENV_DIR="${2:?missing value for --venv-dir}"
      shift 2
      ;;
    --with-pdf-build)
      WITH_PDF_BUILD=1
      shift
      ;;
    --with-maintainer-tools)
      WITH_MAINTAINER_TOOLS=1
      shift
      ;;
    --skip-ollama)
      SKIP_OLLAMA=1
      shift
      ;;
    --ensure-ollama-model)
      ENSURE_OLLAMA_MODEL=1
      shift
      ;;
    --refresh-active-sources)
      REFRESH_ACTIVE_SOURCES=1
      shift
      ;;
    --ollama-base-url)
      OLLAMA_BASE_URL="${2:?missing value for --ollama-base-url}"
      shift 2
      ;;
    --ollama-model)
      OLLAMA_MODEL="${2:?missing value for --ollama-model}"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "${PYTHON_BIN}" ]]; then
  if command -v python3.11 >/dev/null 2>&1; then
    PYTHON_BIN="python3.11"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  else
    echo "No suitable Python interpreter found. Install Python 3.11+ or pass --python <path>." >&2
    exit 2
  fi
fi

VENV_PYTHON="${VENV_DIR}/bin/python"
VENV_SENGENT="${VENV_DIR}/bin/sengent"
VENV_ACTIVATE="${VENV_DIR}/bin/activate"
INSTALL_TARGET="."
if [[ "${WITH_MAINTAINER_TOOLS}" -eq 1 ]]; then
  INSTALL_TARGET=".[maintainer]"
elif [[ "${WITH_PDF_BUILD}" -eq 1 ]]; then
  INSTALL_TARGET=".[pdf-build]"
fi

run_repo_cmd() {
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    printf '+ (cd %s && %s)\n' "${REPO_ROOT}" "$*"
    return 0
  fi
  (
    cd "${REPO_ROOT}"
    "$@"
  )
}

run_cmd() {
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    printf '+ %s\n' "$*"
    return 0
  fi
  "$@"
}

run_repo_doctor() {
  local doctor_args=("doctor")
  if [[ "${SKIP_OLLAMA}" -eq 1 ]]; then
    doctor_args+=("--skip-ollama")
  fi
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    printf '+ (cd %s && OLLAMA_BASE_URL=%s OLLAMA_MODEL=%s %s %s)\n' \
      "${REPO_ROOT}" "${OLLAMA_BASE_URL}" "${OLLAMA_MODEL}" "${VENV_SENGENT}" "${doctor_args[*]}"
    return 0
  fi
  (
    cd "${REPO_ROOT}"
    OLLAMA_BASE_URL="${OLLAMA_BASE_URL}" OLLAMA_MODEL="${OLLAMA_MODEL}" \
      "${VENV_SENGENT}" "${doctor_args[@]}"
  )
}

resolve_default_source_dir() {
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    printf '<default source dir via sengent install>'
    return 0
  fi
  "${VENV_PYTHON}" -c 'from sentieon_assist.app_paths import default_source_dir; print(default_source_dir())'
}

seed_active_source_packs() {
  local target_dir
  local managed_files=(
    "sentieon-modules.json"
    "workflow-guides.json"
    "external-format-guides.json"
    "external-tool-guides.json"
    "external-error-associations.json"
    "incident-memory.json"
  )

  if [[ "${DRY_RUN}" -eq 1 ]]; then
    printf '+ Seed active source packs into %s (including incident-memory.json)\n' "$(resolve_default_source_dir)"
    return 0
  fi

  target_dir="$(resolve_default_source_dir)"
  mkdir -p "${target_dir}"
  for file_name in "${managed_files[@]}"; do
    if [[ ! -f "${REPO_ROOT}/sentieon-note/${file_name}" ]]; then
      echo "Missing source seed file: ${REPO_ROOT}/sentieon-note/${file_name}" >&2
      exit 2
    fi
    if [[ "${REFRESH_ACTIVE_SOURCES}" -eq 1 || ! -f "${target_dir}/${file_name}" ]]; then
      cp "${REPO_ROOT}/sentieon-note/${file_name}" "${target_dir}/${file_name}"
    fi
  done
  if [[ "${REFRESH_ACTIVE_SOURCES}" -eq 1 ]]; then
    echo "Refreshed active source packs at ${target_dir}."
  else
    echo "Seed active source packs at ${target_dir}."
  fi
}

printf 'Repo root: %s\n' "${REPO_ROOT}"
printf 'Python: %s\n' "${PYTHON_BIN}"
printf 'Virtualenv: %s\n' "${VENV_DIR}"
printf 'PDF build extra: %s\n' "$( [[ "${WITH_PDF_BUILD}" -eq 1 ]] && echo yes || echo no )"
printf 'Maintainer tools: %s\n' "$( [[ "${WITH_MAINTAINER_TOOLS}" -eq 1 ]] && echo yes || echo no )"
printf 'Ollama base URL: %s\n' "${OLLAMA_BASE_URL}"
printf 'Ollama model: %s\n' "${OLLAMA_MODEL}"

run_cmd "${PYTHON_BIN}" -m venv "${VENV_DIR}"
run_repo_cmd "${VENV_PYTHON}" -m pip install --disable-pip-version-check --no-build-isolation "${INSTALL_TARGET}"
seed_active_source_packs
run_repo_doctor

if [[ "${SKIP_OLLAMA}" -eq 1 ]]; then
  echo "This host is set up as a build-only / review host."
  echo "Activate the virtualenv first: source ${VENV_ACTIVATE}"
  echo "Then use the installed command: ${VENV_SENGENT} doctor --skip-ollama"
  echo "If you prefer the shell alias after activation, run: sengent doctor --skip-ollama"
  echo "If you later want chat/runtime on this machine, install/start Ollama, pull ${OLLAMA_MODEL}, then run '${VENV_SENGENT} doctor'."
  echo "Skipping Ollama handling as requested."
  exit 0
fi

echo "Ollama runtime integration uses the local HTTP API at ${OLLAMA_BASE_URL}."
echo "Make sure model ${OLLAMA_MODEL} is available before chat/runtime validation."

if [[ "${ENSURE_OLLAMA_MODEL}" -eq 1 ]]; then
  if command -v ollama >/dev/null 2>&1; then
    run_cmd ollama pull "${OLLAMA_MODEL}"
    run_repo_doctor
  else
    echo "ollama CLI not found; skipping model pull. Install/start Ollama and pull ${OLLAMA_MODEL} manually if needed."
  fi
fi

echo "Next step for a runtime host:"
echo "  1. Activate: source ${VENV_ACTIVATE}"
echo "  2. Confirm runtime readiness: ${VENV_SENGENT} doctor"
echo "  3. If doctor says the model is missing, run: ollama pull ${OLLAMA_MODEL}"
echo "  4. Start using: ${VENV_SENGENT} chat"
echo "  5. After activation, you can also use the short command: sengent"
