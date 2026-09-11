from __future__ import annotations

import argparse
import json
from pathlib import Path

from analysis.classifier import classify
from analysis.skeleton_builder import build_skeleton


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a Wovn repo skeleton from a local path.")
    parser.add_argument("path", type=Path)
    parser.add_argument("--url", default="")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    root = args.path.resolve()
    skeleton = build_skeleton(root, repo_url=args.url, root_name=root.name)
    _, signals = classify(skeleton)
    skeleton.classifier_signals = signals
    payload = skeleton.model_dump(mode="json")
    text = json.dumps(payload, indent=2)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text)
    print(
        f"# files={skeleton.file_count} loc={skeleton.loc} "
        f"languages={[lang.value for lang in skeleton.languages]} "
        f"type={signals['project_type']}",
        file=__import__("sys").stderr,
    )


if __name__ == "__main__":
    main()
