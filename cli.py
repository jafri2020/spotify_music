"""
cli.py — command-line interface for the MusicPlayer module.

Examples:
    python cli.py play "yellow coldplay"
    python cli.py play "viva la vida"
    python cli.py pause
    python cli.py resume
    python cli.py next
    python cli.py prev
    python cli.py volume 40
    python cli.py now

For quick testing you can also just pass the query directly:
    python cli.py "yellow coldplay"
"""

from __future__ import annotations

import argparse
import sys

from music_player import MusicPlayer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Play music on Spotify from the command line.",
    )
    sub = parser.add_subparsers(dest="command")

    p_play = sub.add_parser("play", help="search and play a song")
    p_play.add_argument("query", nargs="+", help="song to play, e.g. 'yellow coldplay'")

    sub.add_parser("pause", help="pause playback")
    sub.add_parser("resume", help="resume playback")
    sub.add_parser("next", help="skip to next track")
    sub.add_parser("prev", help="skip to previous track")
    sub.add_parser("now", help="show what's playing")

    p_vol = sub.add_parser("volume", help="set volume 0-100")
    p_vol.add_argument("percent", type=int)

    return parser


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]

    # Convenience: if first arg isn't a known command, treat the whole input
    # as a play query. So `python cli.py yellow coldplay` just works.
    known = {"play", "pause", "resume", "next", "prev", "volume", "now", "-h", "--help"}
    if argv and argv[0] not in known:
        argv = ["play", *argv]

    args = build_parser().parse_args(argv)

    if not args.command:
        build_parser().print_help()
        return 1

    player = MusicPlayer()

    if args.command == "play":
        query = " ".join(args.query)
        result = player.play(query)
        print(result)
        return 0 if result.success else 1

    if args.command == "pause":
        player.pause()
        print("⏸  paused")
        return 0

    if args.command == "resume":
        player.resume()
        print("▶  resumed")
        return 0

    if args.command == "next":
        player.next_track()
        print("⏭  next")
        return 0

    if args.command == "prev":
        player.previous_track()
        print("⏮  previous")
        return 0

    if args.command == "volume":
        player.set_volume(args.percent)
        print(f"🔊 volume set to {args.percent}")
        return 0

    if args.command == "now":
        info = player.now_playing()
        if info is None:
            print("nothing is playing")
            return 0
        state = "playing" if info["is_playing"] else "paused"
        print(f"{state}: {info['name']} — {info['artist']} on {info['device']}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
