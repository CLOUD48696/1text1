"""Package tracked source plus verified PDFs, never local secrets or runtime data."""
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
BLOCKED_DIRS = {'.git', '.venv', 'node_modules', 'dist', '__pycache__', '.pytest_cache',
                'playwright-report', 'test-results', '.codex', 'tmp'}
BLOCKED_SUFFIXES = {'.db', '.sqlite', '.sqlite3', '.log', '.pyc', '.zip'}


def allowed(path):
    p = PurePosixPath(path)
    return not (BLOCKED_DIRS.intersection(p.parts) or p.suffix in BLOCKED_SUFFIXES
                or (p.name.startswith('.env') and p.name != '.env.example')
                or path.startswith('output/delivery/'))


if __name__ == '__main__':
    status = subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=ROOT)
    if status.strip():
        raise SystemExit('请先提交已跟踪文件的变更，保证交付包与 Git 版本一致。')
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode('utf-8').split('\0')
    files = sorted(p for p in tracked if p and allowed(p))
    required = {'README.md', 'backend/app/seed.py', 'backend/requirements.lock.txt',
                'docs/development-prompts.md', 'output/pdf/workflow.pdf', 'output/pdf/development-prompts.pdf'}
    if not required.issubset(files):
        raise SystemExit('交付缺少必要文件：' + ', '.join(sorted(required - set(files))))
    records = [{'path': p, 'sha256': hashlib.sha256((ROOT / p).read_bytes()).hexdigest()} for p in files]
    manifest = {'revision': revision, 'file_count': len(files), 'files': records,
                'runtime_mode': 'demo by default; configure live mode for DeepSeek'}
    output = ROOT / 'output' / 'delivery'
    output.mkdir(parents=True, exist_ok=True)
    archive = output / 'ai-panel-studio.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(ROOT / p, 'ai-panel-studio/' + p)
        z.writestr('ai-panel-studio/DELIVERY-MANIFEST.json', json.dumps(manifest, ensure_ascii=False, indent=2))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for record in records:
            actual = z.read('ai-panel-studio/' + record['path'])
            assert hashlib.sha256(actual).hexdigest() == record['sha256']
        assert len(z.namelist()) == len(files) + 1
        assert all(allowed(p.removeprefix('ai-panel-studio/')) for p in z.namelist())
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output / 'ai-panel-studio.zip.sha256').write_text(f'{digest}  ai-panel-studio.zip\n', encoding='utf-8')
    print(json.dumps({'archive': str(archive), 'revision': revision, 'file_count': len(files),
                      'bytes': archive.stat().st_size, 'sha256': digest}, ensure_ascii=False))
