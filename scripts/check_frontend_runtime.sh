#!/usr/bin/env bash
set -euo pipefail

printf 'Node: %s\n' "$(node --version)"
printf 'npm : %s\n' "$(npm --version)"
printf 'node: %s\n' "$(command -v node)"
printf 'npm : %s\n' "$(command -v npm)"

NODE_MAJOR="$(node -p 'Number(process.versions.node.split(".")[0])')"
NODE_MINOR="$(node -p 'Number(process.versions.node.split(".")[1])')"

if (( NODE_MAJOR < 20 )); then
  echo "FAIL: Node >=20.19 is required. Run: source ~/.bashrc && cd frontend && nvm use"
  exit 1
fi
if (( NODE_MAJOR == 20 && NODE_MINOR < 19 )); then
  echo "FAIL: Node 20 must be >=20.19. Run: source ~/.bashrc && cd frontend && nvm use"
  exit 1
fi

echo "PASS: frontend runtime satisfies Node >=20.19."
