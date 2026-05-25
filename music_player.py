"""
music_player.py — Spotipy-based music player module.

Designed as a standalone module so it can later be imported into a LangGraph
chatbot. The public surface is the MusicPlayer class. The CLI in cli.py is
just a thin wrapper around it.

Usage from code:
    from music_player import MusicPlayer
    player = MusicPlayer()
    result = player.play("yellow coldplay")
    print(result)

Requires:
    pip install spotipy python-dotenv
    Spotify Premium account
    Spotify desktop client running on this machine (or any Spotify Connect device)
    A .env file in the same directory with:
        SPOTIPY_CLIENT_ID=...
        SPOTIPY_CLIENT_SECRET=...
        SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Optional

import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Scopes needed for playback control + reading current state.
# user-modify-playback-state -> start/pause/skip/volume
# user-read-playback-state   -> list devices, see what's playing
SCOPES = "user-modify-playback-state user-read-playback-state"


@dataclass
class PlayResult:
    """Result of a play() call. Designed to be easy for an LLM tool to consume."""
    success: bool
    track_name: Optional[str] = None
    artist: Optional[str] = None
    device_name: Optional[str] = None
    latency_seconds: Optional[float] = None
    error: Optional[str] = None

    def __str__(self) -> str:
        if self.success:
            return (
                f"▶  Now playing: {self.track_name} — {self.artist} "
                f"on {self.device_name} (took {self.latency_seconds:.2f}s)"
            )
        return f"✗ Could not play: {self.error}"


class MusicPlayerError(Exception):
    """Raised when the player cannot fulfill a request."""


class MusicPlayer:
    """
    Thin wrapper around Spotipy that turns a natural-language song query
    into actual audio playback on the user's active Spotify device.

    Design notes:
    - Lazy auth: we only talk to Spotify on first call, so import is cheap.
    - Active-device handling: if no device is active, we try to wake the
      most recently used one via transfer_playback().
    - All methods return data or raise MusicPlayerError. Never silent failure.
    """

    def __init__(self, cache_path: str = ".spotify_cache"):
        # Load .env if python-dotenv is available. Optional dependency.
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

        # Spotipy's SpotifyOAuth reads SPOTIPY_CLIENT_ID / _SECRET / _REDIRECT_URI
        # from the environment by default. Cache file stores the refresh token
        # so the OAuth browser flow only happens once per machine.
        auth_manager = SpotifyOAuth(
            scope=SCOPES,
            cache_path=cache_path,
            open_browser=True,
        )
        self._sp = spotipy.Spotify(auth_manager=auth_manager)

    # ---------- public API ----------

    def play(self, query: str) -> PlayResult:
        """
        Search for `query` on Spotify and start playback of the top match.
        This is the main entry point for the chatbot.
        """
        start = time.perf_counter()
        try:
            track = self._search_top_track(query)
            device_id, device_name = self._ensure_active_device()
            self._sp.start_playback(device_id=device_id, uris=[track["uri"]])
            elapsed = time.perf_counter() - start
            return PlayResult(
                success=True,
                track_name=track["name"],
                artist=", ".join(a["name"] for a in track["artists"]),
                device_name=device_name,
                latency_seconds=elapsed,
            )
        except MusicPlayerError as e:
            return PlayResult(success=False, error=str(e))
        except spotipy.SpotifyException as e:
            return PlayResult(success=False, error=f"Spotify API error: {e.msg}")

    def pause(self) -> None:
        self._sp.pause_playback()

    def resume(self) -> None:
        # start_playback with no args resumes whatever was last playing.
        self._sp.start_playback()

    def next_track(self) -> None:
        self._sp.next_track()

    def previous_track(self) -> None:
        self._sp.previous_track()

    def set_volume(self, percent: int) -> None:
        if not 0 <= percent <= 100:
            raise ValueError("volume must be between 0 and 100")
        self._sp.volume(percent)

    def now_playing(self) -> Optional[dict]:
        """Return a small dict describing the current track, or None if nothing playing."""
        current = self._sp.current_playback()
        if not current or not current.get("item"):
            return None
        item = current["item"]
        return {
            "name": item["name"],
            "artist": ", ".join(a["name"] for a in item["artists"]),
            "is_playing": current["is_playing"],
            "progress_ms": current.get("progress_ms"),
            "duration_ms": item.get("duration_ms"),
            "device": current.get("device", {}).get("name"),
        }

    # ---------- internals ----------

    def _search_top_track(self, query: str) -> dict:
        """Run a Spotify search and return the top track, or raise."""
        results = self._sp.search(q=query, type="track", limit=1)
        items = results.get("tracks", {}).get("items", [])
        if not items:
            raise MusicPlayerError(f"No tracks found for query: {query!r}")
        return items[0]

    def _ensure_active_device(self) -> tuple[str, str]:
        """
        Find a device to play on. Returns (device_id, device_name).

        Strategy:
          1. If there's already an active device, use it.
          2. Otherwise, pick the first available device and transfer playback
             to it. This wakes up the Spotify desktop client.
          3. If no devices at all, raise — the user needs to open Spotify
             on some machine in their account.
        """
        devices = self._sp.devices().get("devices", [])
        if not devices:
            raise MusicPlayerError(
                "No Spotify devices found. Open the Spotify desktop app "
                "(or any Spotify client) on a device logged into this account."
            )

        # Prefer an already-active device.
        for d in devices:
            if d.get("is_active"):
                return d["id"], d["name"]

        # No active device — wake the first one up.
        target = devices[0]
        self._sp.transfer_playback(device_id=target["id"], force_play=False)
        # Small grace period for Spotify to register the transfer before we
        # send start_playback. Without this, the first play() call after a
        # cold start sometimes 404s with NO_ACTIVE_DEVICE.
        time.sleep(0.5)
        return target["id"], target["name"]
