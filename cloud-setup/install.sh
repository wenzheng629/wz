#!/usr/bin/env bash
set -euo pipefail

# Reproduce the verified preparation. The MOOSE dependency installation and
# application build remain blocked on network access to conda.software.inl.gov.
setup_dir=/workspace/.cloud-setup
mkdir -p "$setup_dir/downloads" "$setup_dir/bin"

archive="$setup_dir/downloads/micromamba-2.9.0-0.tar.bz2"
if [ ! -f "$archive" ]; then
  curl -fsSL --retry 2 https://conda.anaconda.org/conda-forge/linux-64/micromamba-2.9.0-0.tar.bz2 -o "$archive"
fi
printf '%s  %s\n' 8761c382127e6363bd9e0a2451aa3ef90d071a79133f736e2f759a3bf13040dd "$archive" | sha256sum -c -
if [ ! -x "$setup_dir/bin/micromamba" ]; then
  tar -xjf "$archive" -C "$setup_dir" bin/micromamba
fi
"$setup_dir/bin/micromamba" --version

# This is a pinned dependency checkout, not another application repository.
moose_dir="$setup_dir/moose"
if [ ! -e "$moose_dir" ]; then
  git clone --depth 1 --branch 2025-09-05-release --filter=blob:none --sparse https://github.com/idaholab/moose.git "$moose_dir"
  git -C "$moose_dir" sparse-checkout set framework modules python scripts test
fi
test "$(git -C "$moose_dir" rev-parse HEAD)" = 832d6f35e1f6c687880270d8bcb23156974cc031
test -f "$moose_dir/framework/app.mk"

# Install only the requested skill; do not copy the source repo's model settings.
source_dir=$(mktemp -d /tmp/ars-codex-install.XXXXXX)
trap 'rm -rf -- "$source_dir"' EXIT
git clone --quiet --depth 1 --branch main https://github.com/Imbad0202/academic-research-skills-codex.git "$source_dir/repo"
ars_commit=71528d9349bcdacfbe94111f06d9e2d82215a44d
if [ "$(git -C "$source_dir/repo" rev-parse HEAD)" != "$ars_commit" ]; then
  git -C "$source_dir/repo" fetch --depth 1 origin "$ars_commit"
  git -C "$source_dir/repo" checkout --detach "$ars_commit"
fi
test "$(git -C "$source_dir/repo" rev-parse HEAD)" = "$ars_commit"
python3 - "$source_dir/repo/skills/academic-research-suite" "$HOME/.agents/skills/academic-research-suite" <<'PY'
import hashlib
import json
import pathlib
import shutil
import sys

src, dst = map(pathlib.Path, sys.argv[1:])
if not dst.exists():
    shutil.copytree(src, dst)
files = [p for p in src.rglob('*') if p.is_file()]
for p in files:
    target = dst / p.relative_to(src)
    if not target.is_file() or hashlib.sha256(p.read_bytes()).digest() != hashlib.sha256(target.read_bytes()).digest():
        raise SystemExit(f'Existing skill differs; preserved without overwriting: {target}')
assert len(list(dst.rglob('SKILL.md'))) == 1
assert json.loads((dst / 'manifest.json').read_text())['adapter_version'] == '3.23.1'
for name in ['deep-research', 'academic-paper', 'academic-paper-reviewer', 'academic-pipeline', 'sr-screener', 'experiment-agent']:
    assert (dst / 'ars' / name / 'WORKFLOW.md').is_file(), name
print(f'ARS-Codex v3.23.1 installed/verified: {dst}; {len(files)} source files')
PY
skill_dir="$HOME/.agents/skills/academic-research-suite"
python3 "$skill_dir/codex/scripts/ars_codex_quality_gates.py" single-root-skill --json
python3 "$skill_dir/codex/scripts/ars_codex_quality_gates.py" root-router --json
printf '%s\n' 'Preparation verified. MOOSE application setup is incomplete until its official dependencies can be installed and its build/tests pass.'
