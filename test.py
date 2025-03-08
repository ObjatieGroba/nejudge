import sys
from pathlib import Path
import argparse
import subprocess
import typing as tp
import os
import re
import shlex
import glob
import time
try:
    from functools import cache
except ImportError:
    def cache(func):
        return func
from typing import Optional, Tuple
import difflib
import json
import yaml


nejudge_path = Path(os.path.realpath(__file__)).parent


def check_ban(regex_filter, text, name='common', reason=None) -> bool:
    found = regex_filter.search(text)
    if found:
        descr = f'\nReason: {reason}' if reason else f' ({name.lower()})'
        print(f"Found banned sequence '{found[0].strip()}' by {repr(regex_filter.pattern)}{descr}\n")
        return False
    return True


def check_req(regex_filter, text, name, reason=None) -> bool:
    found = regex_filter.search(text)
    if not found:
        pre_descr = f' {name.lower()}' if not reason else ''
        post_descr = f'\nReason: {reason}' if reason else ''
        print(f"Did not find required sequence{pre_descr} {repr(regex_filter.pattern)}{post_descr}\n")
        return False
    return True


def extract_solution_without_includes(file: str) -> str:
    lines = []
    with open(file, 'r') as f:
        for i, orig_line in enumerate(f):
            line = orig_line.strip()
            if line.startswith('#include') or line.startswith('#define') or line.startswith('#pragma'):
                continue
            elif line.startswith('#'):
                raise RuntimeError(f'Line markers are not allowed. Bad line {i}: {repr(line)}')
            else:
                lines.append(orig_line)
    return ''.join(lines)


def preprocess(file: str):
    compiler_cmd = 'g++' if file.endswith('.cpp') else 'gcc'  # Not sure if there's any difference
    proc = subprocess.run([compiler_cmd, '-E', '-'], input=extract_solution_without_includes(file).encode(),
                          capture_output=True)
    if proc.returncode != 0:
        print('Preprocessor returned error:')
        try:
            print(proc.stderr.decode())
        except UnicodeError:
            print(proc.stderr)
        exit(1)

    try:
        preprocessed = proc.stdout.decode()
    except UnicodeError:
        print('Source is binary')
        exit(1)

    lines = []
    in_source = False
    source_found = False
    for i, line in enumerate(preprocessed.splitlines(keepends=True)):
        m = re.match(r'# \d+ "(.+?)"', line)
        if m:
            # There still may be multiple <stdin> line markers,
            # e.g. if there are some comment-only lines which are stripped by the preprocessor (but not always?)
            filename = m.group(1)
            if filename == '<stdin>':
                in_source = True
                source_found = True
            else:
                in_source = False
        elif in_source:
            lines.append(line)

    if not source_found:
        raise RuntimeError('<stdin> line markers were not found in preprocessed source:\n'
                           f'\n==========\n{preprocessed}\n==========')
    return ''.join(lines)


@cache
def get_source(source_file: str, use_preprocessor_: bool = True) -> str:
    if use_preprocessor_:
        return preprocess(source_file)
    else:
        with open(source_file, 'r') as f:
            return f.read()


def check(source_file, regex_str, check_func, **extra) -> bool:
    text = get_source(source_file)
    flags = 0
    flags |= re.IGNORECASE
    flags |= re.DOTALL
    regex_filter = re.compile(regex_str, flags)
    return check_func(regex_filter, text, **extra)


def split_reason(regex: str) -> Tuple[str, Optional[str]]:
    parts = regex.rsplit(';;', 1)
    if len(parts) == 1:
        return parts[0], None
    elif len(parts) != 2:
        raise RuntimeError("Incorrect val " + regex)
    return parts  # type: ignore


def load_legacy_clang_format_file() -> str:
    with open(nejudge_path / '.clang-format-11') as f:
        return json.dumps(yaml.safe_load(f))


def check_clang_format_version(source_file: str, format_file: str) -> tp.List[str]:
    def helper(msg):
        print(f'Clang-format minimal required {required_version}. Suggested 15')
        print('To install on debian run: `apt install clang-format`')
        print()
        print('If default version is lower than required \n'
              '  install specified version that can be found by \n'
              '  `apt-cache search clang-format`')
        print('After installation link this version to clang-format. \n'
              '  For 12: \n'
              '  `ln -s /usr/bin/clang-format-12 /usr/local/bin/clang-format`')
        raise RuntimeError(msg)
    args = ['clang-format', '--version']
    proc = subprocess.run(args, capture_output=True)
    required_version = 11
    suggested_version = 15
    if proc.returncode != 0:
        helper('clang-format is not installed!!!')
    version = re.findall(r'\d+', proc.stdout.decode())
    if not version:
        helper('Unable to parse version from "' + proc.stdout.decode() + '"')
    major = int(version[0])
    if major < required_version:
        helper(f'clang-format version {major} is not supported')
    if major < suggested_version:
        print("WARNING: Use legacy clang-format file.")
        return ['python3', f'{nejudge_path}/tools/run-clang-format.py', '--style', load_legacy_clang_format_file(), source_file]
    return ['python3', f'{nejudge_path}/tools/run-clang-format.py', '--style', f'file:{format_file}', source_file]


def run_clang_format(source_file: str, format_file: str, ci: bool):
    if ci:
        return
    args = check_clang_format_version(source_file, format_file)
    proc = subprocess.run(args, capture_output=True)
    if proc.returncode == 0:
        return
    print('Clang-format returned error(s):')
    try:
        print(proc.stderr.decode())
    except UnicodeError:
        print(proc.stderr)
    try:
        print(proc.stdout.decode())
    except UnicodeError:
        print(proc.stdout)
    if ci:
        raise RuntimeError("Clang-format not passed")
    fix = input('Clang-format is not passed. Fix code? (Y/n)')
    if fix and fix.lower() not in ('y', 'yes'):
        raise RuntimeError("Clang-format not passed")
    args.append('-i')
    proc = subprocess.run(args, capture_output=True)
    if proc.returncode == 0:
        return
    raise RuntimeError(f"Unexpected failure while fixing code {proc.returncode}")


def check_style(source_file_wildcard: str, ci: bool):
    for source_file in glob.glob(source_file_wildcard):
        if not os.path.isfile(source_file):
            print("WARNING:", source_file, "is not valid source file")
            continue
        if source_file.endswith('.c') or source_file.endswith('.cpp') or source_file.endswith('.hpp'):
            clang_format_file = nejudge_path / '.clang-format'
            if clang_format_file.is_file():
                run_clang_format(source_file, str(clang_format_file), ci)

        regex_checks_passed = True
        regex_filter = os.environ.get('EJ_BAN_BY_REGEX', '')
        if regex_filter:
            regex_filter, reason = split_reason(regex_filter)
            regex_checks_passed &= check(source_file, regex_filter, check_ban, reason=reason)

        for key, value in os.environ.items():
            if key.startswith('EJ_BAN_BY_REGEX_REQ_'):
                value, reason = split_reason(value)
                value = value.replace(' ', r'\s+')
                regex_checks_passed &= check(source_file, value, check_req, name=key[len('EJ_BAN_BY_REGEX_REQ_'):], reason=reason)
            elif key.startswith('EJ_BAN_BY_REGEX_BAN_'):
                value, reason = split_reason(value)
                value = value.replace(' ', r'\s+')
                regex_checks_passed &= check(source_file, value, check_ban, name=key[len('EJ_BAN_BY_REGEX_BAN_'):], reason=reason)
        if not regex_checks_passed:
            raise RuntimeError("Regex check failed")


def get_child_pid(pid: int) -> int:
    for i in range(10):
        p = subprocess.run(['ps', '--ppid', str(pid), '-o', 'pid='], capture_output=True)
        if p.stdout.strip():
            return int(p.stdout.strip())
        time.sleep(0.1)
    raise RuntimeError(f"No child process of {pid} found")


def check_exit_code(code: int, pat: str) -> bool:
    if pat == '!0':
        return code != 0
    return str(code) == pat


class Initializer:
    def __init__(self, cmd: tp.Optional[str], input_file, correct_file, inf_file, env):
        self.cmd = shlex.split(cmd) if cmd else None
        self.input_file = input_file
        self.correct_file = correct_file
        self.inf_file = inf_file
        self.env = env

    def __enter__(self):
        if self.cmd:
            p = subprocess.Popen(self.cmd + ['start', str(self.input_file), str(self.correct_file), str(self.inf_file)],
                                 shell=False, env=self.env)
            p.communicate()
            if p.returncode != 0:
                raise RuntimeError(f"Failed to run initializer start {p.returncode}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.cmd:
            p = subprocess.Popen(self.cmd + ['stop', str(self.input_file), str(self.correct_file), str(self.inf_file)],
                                 shell=False, env=self.env)
            p.communicate()
            if p.returncode != 0:
                print(f"WARN: Failed to run initializer stop {p.returncode}")


def run_solution(input_file: Path, correct_file: Path, inf_file: Path, cmd: str, params: str,
                 output_file: tp.Optional[str], env_add: tp.Optional[tp.Dict[str, str]],
                 interactor: tp.Optional[str], initializer: tp.Optional[str], user: tp.Optional[str],
                 meta: tp.Dict[str, tp.Any], is_pipeline: bool) -> bytes:
    params = params.replace('input.txt', str(input_file))
    cmd = cmd.replace('input.txt', str(input_file))
    cmd = cmd.replace('test_name', 'tests/' + input_file.name.removesuffix('.dat'))
    if 'params' in cmd:
        cmd = f'{cmd.replace("params", str(params))}'.strip()
    else:
        cmd = f'{cmd} {params}'.strip()
    if user:
        cmd = f'sudo -E -u {user} ' + cmd
    print(cmd, flush=True)
    env = os.environ
    if env_add:
        env = env.copy()
        env.update(env_add)
    before_children_user = os.times().children_user
    with Initializer(initializer, input_file, output_file, inf_file, env):
        if interactor:
            p = subprocess.Popen(shlex.split(cmd), stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=False, env=env)
            pid = p.pid
            if user:
                try:
                    pid = get_child_pid(pid)
                except Exception:
                    print("Failed to start solution", p.returncode)
                    raise
            int_cmd = [interactor, str(input_file),
                       'output', str(correct_file),
                       str(pid), str(inf_file) if inf_file.is_file() else '']
            print(shlex.join(int_cmd), flush=True)
            interactor_env = env.copy()
            interactor_env.update(meta.get('interactor_env', {}))
            i = subprocess.Popen(int_cmd, stdin=p.stdout.fileno(), stdout=p.stdin.fileno(), shell=False, env=interactor_env)
            p.stdout.close()
            p.stdin.close()
            p.wait()
            i.wait()
            if i.returncode != 0:
                if os.path.isfile('output'):
                    with open('output', 'rb') as f:
                        print(f.read().decode(errors='replace'))
                    print()
                raise RuntimeError(f'Interactor failed with code {i.returncode} on test {input_file}')
            with open('output', 'rb') as f:
                res = f.read()
        else:
            with open(input_file) as fin:
                p = subprocess.Popen(shlex.split(cmd), stdin=fin, stdout=subprocess.PIPE, shell=False, env=env)
                res, _ = p.communicate()
    if not check_exit_code(p.returncode, meta.get('exit_code', '0')):
        print(res)
        raise RuntimeError(f'Solution failed with code {p.returncode} on test {input_file}, expected: ', meta.get('exit_code', '0'))
    if output_file:
        if res:
            raise RuntimeError(f'Unexpected output on test {input_file}')
        with open(output_file, 'rb') as f:
            res = f.read()
        os.remove(output_file)
    after_children_user = os.times().children_user
    real_time_limit = meta.get('time_limit', float(os.environ.get('EJUDGE_REAL_TIME_LIMIT_MS', 1.)))
    if after_children_user - before_children_user > real_time_limit:
        if is_pipeline:
            raise RuntimeError(f'Time limit exceed: {after_children_user - before_children_user} > {real_time_limit} secs')
        else:
            print('ERROR:', f'Time limit exceed: {after_children_user - before_children_user} > {real_time_limit} secs')
    return res


def parse_inf_file(f):
    res = {
        'time_limit': float(os.environ.get('EJUDGE_REAL_TIME_LIMIT_MS', 1.)),
    }

    def parse_param(key, val):
        if key == 'params':
            if key in res:
                raise RuntimeError("Duplicated params")
            res[key] = val
        elif key == 'environ' or key == 'compiler_env':
            key = 'environ'
            if not key in res:
                res[key] = {}
            eq = val.find('=')
            if not eq:
                raise RuntimeError("Unsupported env " + repr(val))
            if len(val) > 2 and val[0] == '"' == val[-1]:
                res[key][val[1: eq]] = val[eq + 1: -1]
            else:
                res[key][val[: eq]] = val[eq + 1:]
        elif key == 'interactor_env':
            if key not in res:
                res[key] = {}
            eq = val.find('=')
            if not eq:
                raise RuntimeError("Unsupported env " + repr(val))
            if len(val) > 2 and val[0] == '"' == val[-1]:
                res[key][val[1: eq]] = val[eq + 1: -1]
            else:
                res[key][val[: eq]] = val[eq + 1:]
        elif key == 'comment':
            pass
        elif key == 'time_limit_ms':
            res['time_limit'] = int(val) / 1000
        elif key == 'exit_code':
            if key in res:
                raise RuntimeError("Duplicated params")
            res[key] = val
        else:
            raise RuntimeError(f"Unknown inf param {key} = {val}")

    for line in f.readlines():
        if not line.strip():
            continue
        if ' = ' in line:
            key, val = line.split(' = ', maxsplit=1)
            val = val.strip()
            parse_param(key, val)
        elif line.endswith(' =\n'):
            continue
        else:
            raise RuntimeError(f"Unknown param '{line}'")
    return res


def res_checker(res: bytes, ans: Path, checker: str):
    with open(ans, 'rb') as expected:
        to_cmp = expected.read()
    if checker == 'cmp':
        diff = list(difflib.diff_bytes(difflib.unified_diff, to_cmp.split(b'\n'), res.split(b'\n')))
        if diff:
            for line in diff:
                sys.stdout.write(line.decode(errors='replace'))
                if not line.endswith(b'\n'):
                    print()
            raise RuntimeError(f"Output missmatched on test {test}. Check \"output\" file")
    elif checker == 'sorted-lines':
        diff = list(difflib.diff_bytes(difflib.unified_diff, sorted(to_cmp.strip().split(b'\n')), sorted(res.strip().split(b'\n'))))
        if diff:
            for line in diff:
                sys.stdout.write(line.decode(errors='replace'))
                if not line.endswith(b'\n'):
                    print()
            raise RuntimeError(f"Output missmatched on test {test}. Check \"output\" file")
    elif checker == 'cmp-double':
        eps = float(os.environ.get('EPS', 0))
        res_f = float(res.decode().strip())
        ans_f = float(to_cmp.decode().strip())
        if abs(res_f - ans_f) > eps:
            raise RuntimeError(f'{res} != {ans_f} for EPS={eps}')
    elif checker == 'ignore':
        return
    else:
        raise RuntimeError("Unknown checker " + checker)


parser = argparse.ArgumentParser()
parser.add_argument('--prepare-answers', action='store_true')
parser.add_argument('--output-file', required=False)
parser.add_argument('--source-file', default='solution.*')
parser.add_argument('--run-cmd', default='./solution')
parser.add_argument('--checker', default='cmp')
parser.add_argument('--interactor', required=False)
parser.add_argument('--initializer', required=False)
parser.add_argument('--may-fail-local', nargs='+', default=[])
parser.add_argument('--user', required=False)
args = parser.parse_args()

is_pipeline = bool(os.environ.get('GITLAB_CI', None))
retests_amount = int(os.environ.get('EJ_RETESTS_AMOUNT', 1))

if is_pipeline:
    args.may_fail_local = []
else:
    args.user = None

check_style(args.source_file, is_pipeline)

for cnt in range(retests_amount):
    print(f"Trying tests #{cnt}")
    for test in sorted(Path('tests').glob('*.dat')):
        inf = Path(str(test).removesuffix('.dat') + '.inf')
        ans = Path(str(test).removesuffix('.dat') + '.ans')
        meta = {}
        if inf.is_file():
            with open(inf) as f:
                meta = parse_inf_file(f)
        if not ans.is_file() and not args.prepare_answers:
            raise RuntimeError("No answer for test " + test.name)
        res = run_solution(test, ans, inf, args.run_cmd, meta.get('params', ''), args.output_file, meta.get('environ'),
                           args.interactor, args.initializer, args.user, meta, is_pipeline)
        if not args.prepare_answers:
            try:
                res_checker(res, ans, args.checker)
            except:
                if str(test) in args.may_fail_local:
                    print(f"Test {test} skipped")
                else:
                    with open('output', 'wb') as f:
                        f.write(res)
                    raise
        else:
            with open(ans, 'wb') as fout:
                fout.write(res)

print("All tests passed")
