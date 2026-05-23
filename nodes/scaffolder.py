import os
import tempfile
import git
from state import State


def _git_stdin(repo: git.Repo, cmd: list, input_text: str) -> str:
    """Run a git command with stdin input via a temp file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(input_text)
        tmp_path = f.name
    try:
        with open(tmp_path, "r") as f:
            result = repo.git.execute(cmd, istream=f)
    finally:
        os.unlink(tmp_path)
    return result


def scaffolder_node(state: State):
    output_dir = state["output_dir"]

    # Resolve path: absolute as-is, relative to cwd
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(os.getcwd(), output_dir)

    output_dir = os.path.normpath(output_dir)
    bare_path = output_dir + ".git"

    # Init bare repo if it doesn't exist
    if not os.path.exists(bare_path):
        bare_repo = git.Repo.init(bare_path, bare=True)
        print(f"\nBare repo created at: {bare_path}")
    else:
        bare_repo = git.Repo(bare_path)
        print(f"\nBare repo already exists at: {bare_path}")

    # 1. Write plan.md as a blob using a real temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(state["plan"])
        tmp_plan = f.name
    try:
        blob_hash = bare_repo.git.execute(["git", "hash-object", "-w", tmp_plan])
    finally:
        os.unlink(tmp_plan)

    # 2. Create a tree containing plan.md
    tree_hash = _git_stdin(
        bare_repo,
        ["git", "mktree"],
        f"100644 blob {blob_hash}\tplan.md\n",
    )

    # 3. Create the initial commit on main
    commit_hash = bare_repo.git.commit_tree(tree_hash, "-m", "Add plan.md")

    # 4. Point main at the commit and set HEAD
    bare_repo.git.update_ref("refs/heads/main", commit_hash)
    bare_repo.git.symbolic_ref("HEAD", "refs/heads/main")
    print("plan.md committed to main branch.")

    # 5. Create release branch pointing to the same commit
    bare_repo.git.update_ref("refs/heads/release", commit_hash)
    print("release branch created from main.")

    print(f"\nBranch strategy:")
    print(f"  main    — plan.md lives here; implementation branches off main")
    print(f"  release — merge target when implementation is complete")
    print(f"\nAdd a worktree with: git -C {bare_path} worktree add <path> main")

    return {"output_dir": output_dir}
