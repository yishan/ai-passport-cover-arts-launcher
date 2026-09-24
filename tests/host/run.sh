#!/bin/sh
# Build and run the host tests. Usage: tests/host/run.sh  (CC defaults to cc)
set -eu

here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../.." && pwd)
out=${TMPDIR:-/tmp}/launcher_contract_host_test

${CC:-cc} -std=c99 -Wall -Wextra -Werror -g \
    -I"$here/stubs" \
    -I"$root/assets/launcher_contract/include" \
    -I"$root/examples/cover_return_demo/main" \
    "$here/test_cover_return.c" \
    "$root/assets/launcher_contract/launcher_contract.c" \
    "$root/examples/cover_return_demo/main/play_dispatch.c" \
    -o "$out"

"$out"
