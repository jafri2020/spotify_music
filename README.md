# music_player

Standalone Python module to play Spotify music from a CLI. Designed to later be imported into a LangGraph chatbot without modification.

## Files

| File | Purpose |
|---|---|
| `music_player.py` | The `MusicPlayer` class. Import this from your chatbot. |
| `cli.py` | Command-line wrapper. For testing. |
| `.env.example` | Template for Spotify credentials. Copy to `.env`. |
| `requirements.txt` | Python dependencies. |

## Setup (Windows)

```powershell
# 1. Install dependencies
pip install -r requirements.txt

# 2. Get Spotify credentials
#    - Go to https://developer.spotify.com/dashboard
#    - Create an app
#    - Set redirect URI to exactly:  http://127.0.0.1:8888/callback
#    - Copy Client ID and Secret

# 3. Create your .env file
copy .env.example .env
notepad .env    # paste your real Client ID and Secret

# 4. Make sure the Spotify desktop app is running and logged in to a Premium account
```

## Use

```powershell
# First time only: a browser window will open for OAuth. Approve, and the
# token is cached in .spotify_cache so it won't ask again.

python cli.py play "yellow coldplay"
python cli.py "viva la vida"          # 'play' is the default
python cli.py pause
python cli.py resume
python cli.py next
python cli.py prev
python cli.py volume 40
python cli.py now
```

## Use from code (future chatbot integration)

```python
from music_player import MusicPlayer

player = MusicPlayer()
result = player.play("yellow coldplay")

if result.success:
    print(f"Playing {result.track_name} by {result.artist}")
else:
    print(f"Failed: {result.error}")
```

The `PlayResult` dataclass is structured so it's easy to return from a LangGraph tool node — the LLM can read `track_name`, `artist`, and `error` directly.

## Troubleshooting

**`No Spotify devices found`** — Open the Spotify desktop app on the same machine (or any device logged into the same account) and make sure it's not fully closed. Spotify's API doesn't play audio itself; it commands a Spotify client to play.

**`NO_ACTIVE_DEVICE` even with Spotify running** — Click play on any song manually once to wake the device, then retry. The module's `_ensure_active_device` should handle this automatically via `transfer_playback`, but the very first interaction after a long idle sometimes needs a manual nudge.

**OAuth browser doesn't open / redirect fails** — Make sure the redirect URI in your Spotify Dashboard *exactly* matches the one in `.env`, including `http://` (not `https://`) and the trailing path.

**Playback works but isn't audible** — Check that the Spotify desktop client's output device is set to the speakers you expect (Spotify → Now Playing bar → device picker).

## Latency expectations

Measured end-to-end (`play()` call to audio starting): typically **1.5–3 seconds** on a warm connection. The `latency_seconds` field on `PlayResult` reports this. If you consistently see >5s, check your network and whether the Spotify client is actively connected (look for it in `python cli.py now`).
