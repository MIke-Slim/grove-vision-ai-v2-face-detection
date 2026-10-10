"""Restore pinned Windows SDK/toolchain dependencies, without touching hardware."""
import argparse
import hashlib
import json
import os
import shutil
import ssl
import subprocess
import urllib.request
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
lock = json.loads((root / 'sources.lock.json').read_text(encoding='utf-8'))
parser = argparse.ArgumentParser()
parser.add_argument('--offline', action='store_true', help='Use existing archives only')
args = parser.parse_args()

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def check_archive(path, entry):
    if 'sha256' in entry:
        if sha(path) != entry['sha256']:
            raise RuntimeError(f'Checksum mismatch: {path}')
    else:
        with zipfile.ZipFile(path) as archive:
            if archive.comment.decode('ascii') != entry['commit']:
                raise RuntimeError('SDK ZIP does not match the pinned commit')

def download(entry):
    cache = root / entry['cache']
    cache.parent.mkdir(parents=True, exist_ok=True)
    if cache.exists():
        check_archive(cache, entry)
        return cache
    if args.offline:
        raise FileNotFoundError(f'Offline archive missing: {cache}')
    part = cache.with_suffix(cache.suffix + '.part')
    context = ssl.create_default_context()
    try:
        import certifi
        context.load_verify_locations(certifi.where())
    except ImportError:
        pass
    request = urllib.request.Request(entry['url'], headers={'User-Agent': 'grove-v2-face-workflow'})
    print('Downloading', entry['url'], flush=True)
    with urllib.request.urlopen(request, context=context, timeout=90) as response, part.open('wb') as stream:
        shutil.copyfileobj(response, stream, length=1024 * 1024)
    check_archive(part, entry)
    part.replace(cache)
    return cache

def extract_zip(archive, target):
    target.mkdir(parents=True, exist_ok=True)
    resolved = target.resolve()
    with zipfile.ZipFile(archive) as source:
        for member in source.infolist():
            child = (resolved / member.filename).resolve()
            if not child.is_relative_to(resolved):
                raise RuntimeError('Archive path escapes target')
        source.extractall('\\\\?\\' + str(resolved) if os.name == 'nt' else resolved)

sdk = lock['sdk']
sdk_folder = root / sdk['folder']
if not sdk_folder.exists():
    archive = download(sdk)
    staging = root / '.cache/sdk-extract'
    extract_zip(archive, staging)
    with zipfile.ZipFile(archive) as contents:
        prefix = contents.namelist()[0].split('/')[0]
    extracted = (staging / prefix).resolve()
    if not extracted.is_relative_to(staging.resolve()) or not sdk_folder.resolve().is_relative_to(root.resolve()):
        raise RuntimeError('Unsafe SDK move target')
    sdk_folder.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(extracted), str(sdk_folder))
for relative, expected in sdk['files'].items():
    if sha(sdk_folder / relative) != expected:
        raise RuntimeError(f'SDK baseline differs from the pinned snapshot: {relative}')

arm = lock['arm']
arm_folder = root / arm['folder']
if not (arm_folder / 'bin/arm-none-eabi-g++.exe').exists():
    extract_zip(download(arm), root / 'toolchains')
make_path = root / 'toolchains/mingw64/bin/mingw32-make.exe'
if not make_path.exists():
    archive = download(lock['make'])
    subprocess.run(['tar.exe', '-xf', str(archive), '-C', str(root / 'toolchains')], check=True)
for name, target in [('sdk', sdk_folder), ('tc', arm_folder)]:
    link = root / name
    if link.exists():
        if link.resolve() != target.resolve():
            raise RuntimeError(f'{name} points outside the expected local directory')
    else:
        env = os.environ.copy()
        env['GROVE_LINK_PATH'] = str(link)
        env['GROVE_LINK_TARGET'] = str(target)
        subprocess.run(['powershell.exe', '-NoProfile', '-Command',
            'New-Item -ItemType Junction -Path $env:GROVE_LINK_PATH -Target $env:GROVE_LINK_TARGET | Out-Null'],
            env=env, check=True)
print('Pinned SDK, Arm toolchain, make and directory links are ready.', flush=True)
