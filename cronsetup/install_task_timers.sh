#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  install_task_timers.sh --working-directory <path> --task-name <name> --amount <1-4> [options]

Required:
  -d, --working-directory <path>   WorkingDirectory for the generated service units.
  -t, --task-name <name>           Task name used in unit filenames and descriptions.
  -a, --amount <1-4>               Number of service/timer pairs to install.

Optional:
  -c, --run-count <n>              manage.py task run count per execution (default: 10).
  -i, --interval-minutes <n>       Timer interval in minutes (default: 1).
  -b, --boot-delay <value>         OnBootSec value (default: 10min).
      --compose-bin <path>         Docker compose binary path (default: /usr/bin/docker).
      --python-bin <path>          Python binary inside container (default: /venv/bin/python).
      --manage-path <path>         manage.py path relative to WorkingDirectory (default: manage.py).
      --dry-run                    Print files that would be written; do not modify systemd.
  -h, --help                       Show this help text.

Example:
  sudo ./scripts/install_task_timers.sh \
    --working-directory /k3snz/srht \
    --task-name filehouse \
    --amount 4
EOF
}

ensure_root() {
  if [[ "$(id -u)" -ne 0 ]]; then
    echo "Error: this script must be run as root." >&2
    exit 1
  fi
}

sanitize_name() {
  # Convert user input into a safe unit-name fragment.
  local raw="$1"
  local safe
  safe="$(echo "$raw" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//')"
  if [[ -z "$safe" ]]; then
    echo "Error: --task-name produced an empty unit-safe name." >&2
    exit 1
  fi
  echo "$safe"
}

write_unit_files() {
  local idx="$1"
  local task_name="$2"
  local task_safe="$3"
  local working_dir="$4"
  local run_count="$5"
  local interval_minutes="$6"
  local boot_delay="$7"
  local compose_bin="$8"
  local python_bin="$9"
  local manage_path="${10}"
  local dry_run="${11}"

  local base="${task_safe}-${idx}"
  local service_name="${base}.service"
  local timer_name="${base}.timer"
  local service_path="/etc/systemd/system/${service_name}"
  local timer_path="/etc/systemd/system/${timer_name}"

  local service_content
  service_content="[Unit]
Description=Run ${task_name} Task

[Service]
Type=oneshot
WorkingDirectory=${working_dir}
ExecStart=/bin/sh -c \"${compose_bin} compose exec -T web ${python_bin} ${manage_path} task run -c ${run_count}\"
StandardOutput=journal
StandardError=journal
"

  local timer_content
  timer_content="[Unit]
Description=Run ${task_name} cron every ${interval_minutes} minutes

[Timer]
OnBootSec=${boot_delay}
OnUnitActiveSec=${interval_minutes}min
Persistent=true
Unit=${service_name}

[Install]
WantedBy=timers.target
"

  if [[ "$dry_run" == "true" ]]; then
    echo "--- ${service_path} ---"
    printf '%s\n' "$service_content"
    echo "--- ${timer_path} ---"
    printf '%s\n' "$timer_content"
    return
  fi

  printf '%s\n' "$service_content" > "$service_path"
  printf '%s\n' "$timer_content" > "$timer_path"

  echo "Installed ${service_name} and ${timer_name}"
}

main() {
  local working_dir=""
  local task_name=""
  local amount=""
  local run_count="10"
  local interval_minutes="1"
  local boot_delay="10min"
  local compose_bin="/usr/bin/docker"
  local python_bin="/venv/bin/python"
  local manage_path="manage.py"
  local dry_run="false"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      -d|--working-directory)
        working_dir="$2"
        shift 2
        ;;
      -t|--task-name)
        task_name="$2"
        shift 2
        ;;
      -a|--amount)
        amount="$2"
        shift 2
        ;;
      -c|--run-count)
        run_count="$2"
        shift 2
        ;;
      -i|--interval-minutes)
        interval_minutes="$2"
        shift 2
        ;;
      -b|--boot-delay)
        boot_delay="$2"
        shift 2
        ;;
      --compose-bin)
        compose_bin="$2"
        shift 2
        ;;
      --python-bin)
        python_bin="$2"
        shift 2
        ;;
      --manage-path)
        manage_path="$2"
        shift 2
        ;;
      --dry-run)
        dry_run="true"
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        echo "Error: unknown option $1" >&2
        usage
        exit 1
        ;;
    esac
  done

  if [[ -z "$working_dir" || -z "$task_name" || -z "$amount" ]]; then
    echo "Error: --working-directory, --task-name, and --amount are required." >&2
    usage
    exit 1
  fi

  if [[ ! -d "$working_dir" ]]; then
    echo "Error: working directory does not exist: $working_dir" >&2
    exit 1
  fi

  if ! [[ "$amount" =~ ^[1-4]$ ]]; then
    echo "Error: --amount must be an integer from 1 to 4." >&2
    exit 1
  fi

  if ! [[ "$run_count" =~ ^[1-9][0-9]*$ ]]; then
    echo "Error: --run-count must be a positive integer." >&2
    exit 1
  fi

  if ! [[ "$interval_minutes" =~ ^[1-9][0-9]*$ ]]; then
    echo "Error: --interval-minutes must be a positive integer." >&2
    exit 1
  fi

  ensure_root

  if [[ "$dry_run" != "true" ]] && ! command -v systemctl >/dev/null 2>&1; then
    echo "Error: systemctl not found." >&2
    exit 1
  fi

  local task_safe
  task_safe="$(sanitize_name "$task_name")"

  local i
  for (( i=1; i<=amount; i++ )); do
    write_unit_files \
      "$i" "$task_name" "$task_safe" "$working_dir" "$run_count" \
      "$interval_minutes" "$boot_delay" "$compose_bin" "$python_bin" \
      "$manage_path" "$dry_run"
  done

  if [[ "$dry_run" == "true" ]]; then
    echo "Dry-run complete. No files were written."
    exit 0
  fi

  systemctl daemon-reload

  for (( i=1; i<=amount; i++ )); do
    local timer_name="${task_safe}-${i}.timer"
    systemctl enable --now "$timer_name"
    echo "Enabled and started $timer_name"
  done

  echo "Done. Installed ${amount} timer(s) for task '${task_name}'."
}

main "$@"
