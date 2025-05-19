
import tempfile
import shutil
import subprocess
from pathlib import Path
import os
import re
from typing import List


def find_git_root(path: str):
    """Returns the git root directory for a given path, or None if not in a git repo."""
    _pth = Path(path)
    if _pth.is_file():
        path = str(_pth.parent)

    try:
        result = subprocess.run(
            ['git', '-C', path, 'rev-parse', '--show-toplevel'],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(e)
        return None

def get_git_ignored_paths(git_root):
    """
    Returns a set of all paths (files and directories) excluded by .gitignore.
    """
    try:
        result = subprocess.run(
            ['git', '-C', git_root, 'status', '--ignored', '--porcelain'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        ignored_paths = set()
        for line in result.stdout.splitlines():
            if line.startswith('!! '):
                path = line[3:]
                ignored_paths.add(os.path.join(git_root, path))
        return list(ignored_paths)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to get ignored files: {e.stderr}")


def copy_git_repo_excluding_ignored(src_path, dst_path):
    """Copy contents of a Git repo to dst_path, excluding files ignored by .gitignore."""
    git_root = find_git_root(src_path)
    if git_root is None:
        raise ValueError(f"{src_path} is not inside a Git repository.")

    ignored_abs_paths = list(map(Path, get_git_ignored_paths(git_root) + [os.path.join(src_path, '.git')]))

    for root, dirs, files in os.walk(git_root):
        dirs[:] = [d for d in dirs if Path(os.path.join(root, d)) not in ignored_abs_paths]

        rel_root = os.path.relpath(root, git_root)
        dst_dir = os.path.join(dst_path, rel_root)
        os.makedirs(dst_dir, exist_ok=True)

        for file in files:
            src_file = os.path.join(root, file)
            if not any([i in Path(src_file).parents for i in ignored_abs_paths]):
                dst_file = os.path.join(dst_dir, file)

                if os.path.islink(src_file):
                    link_target = os.readlink(src_file)
                    os.symlink(link_target, dst_file)
                else:
                    shutil.copy2(src_file, dst_file)
                

class TmpCheckoutContext:
    def __init__(self, source_path, idx=0):
        self.source_root = find_git_root(source_path)
        self.tmp_root = None
        self.idx = idx
        self.checked_out = False
    
    def __enter__(self):
        self.tmp_root = tempfile.mkdtemp(prefix='eallm_', suffix=f'_w{self.idx}')
        # TODO: *need* to handle git ignore!
        copy_git_repo_excluding_ignored(self.source_root, self.tmp_root)
        self.checked_out = True
        # shutil.copytree(self.source_root, self.tmp_root, dirs_exist_ok=True)

    def __exit__(self, exception_type, exception_value, exception_traceback):
        if self.checked_out:
            shutil.rmtree(self.tmp_root)
            self.tmp_root = None
            self.checked_out = False
            if exception_type is not None:
                raise exception_value.with_traceback(exception_traceback)




def find_evolve_marked_files(src_path, relpath=False): 
    # Compile the regex pattern with DOTALL to allow multiline matching
    regex = re.compile(r'# EVOLVE START.*\n# EVOLVE END', re.DOTALL)

    git_root = find_git_root(src_path)
    if git_root is None:
        raise ValueError(f"{src_path} is not inside a Git repository.")

    ignored_abs_paths = list(map(Path, get_git_ignored_paths(git_root) + [os.path.join(src_path, '.git')]))
    matching_files = []

    for root, dirs, files in os.walk(git_root):
        dirs[:] = [d for d in dirs if Path(os.path.join(root, d)) not in ignored_abs_paths]

        for file in files:
            src_file = os.path.join(root, file)
            if not any([i in Path(src_file).parents for i in ignored_abs_paths]):
                
                # LOOK FOR IT
                try:
                    with open(src_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if regex.search(content):
                            if relpath:
                                matching_files.append(str(Path(src_file).relative_to(Path(git_root))))
                            else:
                                matching_files.append(src_file)
                            continue
                except (UnicodeDecodeError, PermissionError, IsADirectoryError):
                    # Skip non-text or inaccessible files
                    continue
    
    return matching_files


def find_evolve_marked_sections(content):
    # detect and catalogue how many to-evolve sections there are in the file
    original_part_strs = re.findall(r'# EVOLVE START\n?(.*?)\n# EVOLVE END', content, re.DOTALL)
    return original_part_strs


def find_evolve_marked_file_sections(evolve_fp):
    with open(evolve_fp, 'r') as f:
        content = f.read()
    return find_evolve_marked_sections(content)

def replace_evolve_marked_sections(content, new_sections):
    original_part_strs = find_evolve_marked_sections(content)
    # rolled up sequential replacement
    _idx = 0
    new_content = ''
    for olds, news in zip(original_part_strs, new_sections):
        wrapped_olds = f'# EVOLVE START\n{olds}\n# EVOLVE END'
        wrapped_news = f'# EVOLVE START\n{news}\n# EVOLVE END'
        olds_st_idx = content.find(wrapped_olds)
        olds_en_idx = olds_st_idx + len(wrapped_olds)
        new_content += content[_idx:olds_en_idx].replace(wrapped_olds,wrapped_news)
        _idx = len(new_content)
    new_content += content[olds_en_idx:]
    return new_content


