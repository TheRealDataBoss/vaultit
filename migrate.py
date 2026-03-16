import os

root = r'C:\Users\Steven\vaultit'
os.chdir(root)

# === PHASE 1: Directory and file renames ===
renames = [
    ('packages\\python\\vaultit', 'packages\\python\\vaultit'),
    ('packages\\python\\.vaultit', 'packages\\python\\.vaultit'),
    ('packages\\npm\\bin\\vaultit.js', 'packages\\npm\\bin\\vaultit.js'),
    ('saas\\vaultit_saas', 'saas\\vaultit_saas'),
    ('projects\\vaultit', 'projects\\vaultit'),
]
for old, new in renames:
    old_p = os.path.join(root, old)
    new_p = os.path.join(root, new)
    if os.path.exists(old_p):
        os.rename(old_p, new_p)
        print(f'  Renamed: {old} -> {new}')
    else:
        print(f'  Skip (not found): {old}')

db_old = os.path.join(root, 'packages', 'python', '.vaultit', 'vaultit.db')
db_new = os.path.join(root, 'packages', 'python', '.vaultit', 'vaultit.db')
if os.path.exists(db_old):
    os.rename(db_old, db_new)
    print('  Renamed: vaultit.db -> vaultit.db')

s_old = os.path.join(root, 'protocol', 'vaultit.schema.json')
s_new = os.path.join(root, 'protocol', 'vaultit.schema.json')
if os.path.exists(s_old):
    os.rename(s_old, s_new)
    print('  Renamed: vaultit.schema.json -> vaultit.schema.json')

ps_old = os.path.join(root, 'scripts', 'vaultit_push.ps1')
ps_new = os.path.join(root, 'scripts', 'vaultit_push.ps1')
if os.path.exists(ps_old):
    os.rename(ps_old, ps_new)
    print('  Renamed: vaultit_push.ps1 -> vaultit_push.ps1')

print('\nPhase 1 done.\n')

# === PHASE 2: Text replacements ===
pass1 = [
    ('vaultit_saas', 'vaultit_saas'),
    ('VaultItClient', 'VaultItClient'),
    ('VaultItError', 'VaultItError'),
    ('vaultit_init', 'vaultit_init'),
    ('vaultit_sync', 'vaultit_sync'),
    ('vaultit_status', 'vaultit_status'),
    ('vaultit_bootstrap', 'vaultit_bootstrap'),
    ('vaultit_handoff', 'vaultit_handoff'),
    ('vaultit_session', 'vaultit_session'),
    ('vaultit_task', 'vaultit_task'),
    ('vaultit_decision', 'vaultit_decision'),
    ('vaultit_doctor', 'vaultit_doctor'),
    ('io.github.TheRealDataBoss/vaultit', 'io.github.TheRealDataBoss/vaultit'),
    ('io.github.therealdataboss/vaultit', 'io.github.therealdataboss/vaultit'),
    ('TheRealDataBoss/vaultit', 'TheRealDataBoss/vaultit'),
    ('therealdataboss.github.io/vaultit', 'therealdataboss.github.io/vaultit'),
    ('pypi.org/project/vaultit', 'pypi.org/project/vaultit'),
    ('npmjs.com/package/vaultit', 'npmjs.com/package/vaultit'),
    ('pip install vaultit', 'pip install vaultit'),
    ('npm install -g vaultit', 'npm install -g vaultit'),
    ('npm install vaultit', 'npm install vaultit'),
    ('.vaultit', '.vaultit'),
    ('VAULTIT_', 'VAULTIT_'),
    ('vaultit.ai', 'vaultit.ai'),
    ('vaultit.db', 'vaultit.db'),
    ('vaultit', 'vaultit'),
    ('VaultIt', 'VaultIt'),
    ('VAULTIT', 'VAULTIT'),
]

pass2 = [
    ('vaultit-v1.0', 'vaultit-v1.0'),
    ('vaultit-v', 'vaultit-v'),
    ('$VaultItHome', '$VaultItHome'),
    ('$VaultItBin', '$VaultItBin'),
    ('$VaultItSrc', '$VaultItSrc'),
    ('$VaultItPath', '$VaultItPath'),
    ('VAULTIT_HOME', 'VAULTIT_HOME'),
    ('VAULTIT_BIN', 'VAULTIT_BIN'),
    ('VAULTIT_REPO', 'VAULTIT_REPO'),
    ('VAULTIT_TOKEN', 'VAULTIT_TOKEN'),
    ('VAULTIT_SRC', 'VAULTIT_SRC'),
    ('vaultit_repo', 'vaultit_repo'),
    ('install_vaultit', 'install_vaultit'),
    ('vaultit init', 'vaultit init'),
    ('vaultit sync', 'vaultit sync'),
    ('vaultit status', 'vaultit status'),
    ('vaultit bootstrap', 'vaultit bootstrap'),
    ('vaultit doctor', 'vaultit doctor'),
    ('vaultit --version', 'vaultit --version'),
    ('vaultit.ps1', 'vaultit.ps1'),
    ('vaultit.cmd', 'vaultit.cmd'),
    ('vaultit.js', 'vaultit.js'),
    ('vaultit.schema.json', 'vaultit.schema.json'),
    ('vaultit.cli', 'vaultit.cli'),
    ('vaultit', 'vaultit'),
    ('chore(vaultit)', 'chore(vaultit)'),
    ('VaultIt AI Sync', 'VaultIt AI Sync'),
    ('VaultIt', 'VaultIt'),
    ('VaultIt sync', 'VaultIt sync'),
    ('vaultit bridge repo', 'vaultit bridge repo'),
    ('vaultit bridge', 'vaultit bridge'),
    ('Bash(vaultit', 'Bash(vaultit'),
    ('npm/vaultit', 'npm/vaultit'),
    ('where vaultit', 'where vaultit'),
    ('VaultIt', 'VaultIt'),
    ('vaultit', 'vaultit'),
]

skip_ext = {'.pyc', '.pyo', '.whl', '.gz', '.png', '.jpg', '.gif', '.ico', '.db', '.sqlite3'}
skip_dirs = {'node_modules', '__pycache__', '.git', 'dist', 'build', '.egg-info'}

def do_pass(replacements, label):
    changed = 0
    total = 0
    for rt, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for fn in files:
            ext = os.path.splitext(fn)[1].lower()
            if ext in skip_ext:
                continue
            fp = os.path.join(rt, fn)
            try:
                with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except:
                continue
            original = content
            fc = 0
            for old, new in replacements:
                if old in content:
                    fc += content.count(old)
                    content = content.replace(old, new)
            if content != original:
                with open(fp, 'w', encoding='utf-8') as f:
                    f.write(content)
                changed += 1
                total += fc
    print(f'{label}: {changed} files, {total} replacements')

do_pass(pass1, 'Pass 1 (vaultit)')
do_pass(pass2, 'Pass 2 (vaultit)')

print('\nDone. Verifying...')
count = 0
for rt, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in skip_dirs]
    for fn in files:
        ext = os.path.splitext(fn)[1].lower()
        if ext in skip_ext:
            continue
        fp = os.path.join(rt, fn)
        try:
            c = open(fp, 'r', encoding='utf-8', errors='ignore').read()
            if 'vaultit' in c.lower():
                count += 1
                print(f'  REMAINING: {fp}')
        except:
            pass
if count == 0:
    print('CLEAN: Zero remaining vaultit references.')
else:
    print(f'{count} files still have references.')
print('\nMigration complete.')
