#!/usr/bin/env bash
set -euo pipefail

readonly REMOTE_HOST="ubuntu@1.13.181.58"
readonly REMOTE_CLEANUP_COMMAND='
set -eu
all_pids=""
for port in 40302 40031; do
  listeners="$(sudo -n ss -H -lntp "sport = :${port}" || true)"
  [ -z "${listeners}" ] && continue

  pids="$(printf "%s\n" "${listeners}" | sed -n "s/.*pid=\([0-9][0-9]*\).*/\1/p" | sort -u)"
  [ -n "${pids}" ] || {
    echo "公网端口 ${port} 已被占用，但无法确认占用进程" >&2
    exit 1
  }

  for pid in ${pids}; do
    owner="$(sudo -n ps -p "${pid}" -o user= | xargs)"
    command="$(sudo -n ps -p "${pid}" -o comm= | xargs)"
    if [ "${owner}" != "ubuntu" ] || [ "${command}" != "sshd" ]; then
      echo "拒绝清理非本项目 SSH 转发占用：port=${port} pid=${pid} owner=${owner} command=${command}" >&2
      exit 1
    fi
    all_pids="${all_pids} ${pid}"
  done
done

for pid in $(printf "%s\n" ${all_pids} | sort -u); do
  echo "清理失效的公网 SSH 转发：pid=${pid}" >&2
  sudo -n kill "${pid}"
done

attempt=0
while [ "${attempt}" -lt 20 ]; do
  occupied=0
  for port in 40302 40031; do
    if sudo -n ss -H -lnt "sport = :${port}" | grep -q .; then
      occupied=1
      break
    fi
  done
  [ "${occupied}" -eq 0 ] && exit 0
  attempt=$((attempt + 1))
  sleep 0.25
done

echo "等待公网转发端口释放超时" >&2
exit 1
'

SSH_OPTIONS=(
  -o BatchMode=yes
  -o ConnectTimeout=10
  -o ExitOnForwardFailure=yes
  -o ServerAliveInterval=30
  -o ServerAliveCountMax=3
  -o TCPKeepAlive=yes
  -o StrictHostKeyChecking=yes
)

# 异常断网可能让公网 sshd 暂时保留旧的反向监听。只清理 ubuntu 用户
# 在本项目固定端口上的 sshd 转发；其他进程占用时拒绝继续，避免误杀。
ssh -T "${SSH_OPTIONS[@]}" "${REMOTE_HOST}" "${REMOTE_CLEANUP_COMMAND}"

exec ssh -NT "${SSH_OPTIONS[@]}" \
  -R 0.0.0.0:40302:localhost:40302 \
  -R 0.0.0.0:40031:localhost:40031 \
  "${REMOTE_HOST}"
