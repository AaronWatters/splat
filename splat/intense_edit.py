from __future__ import annotations

import argparse


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="intense-edit")
    parser.add_argument("-i", "--intensities", required=True)
    parser.add_argument("-l", "--labels", default=None)
    parser.add_argument("-w", "--width", type=int, default=500)
    parser.add_argument("--dI", type=int, default=5)
    parser.add_argument("--dJ", type=int, default=5)
    parser.add_argument("--dK", type=int, default=5)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = make_parser().parse_args(argv)

    from splat import edit
    import H5Gizmos as gz

    wrapped = edit.SegmentEditorIO(
        intensities_file=args.intensities,
        labels_file=args.labels,
        width=args.width,
        scaling=(args.dI, args.dJ, args.dK),
    )
    gz.serve(wrapped.gizmo.link())