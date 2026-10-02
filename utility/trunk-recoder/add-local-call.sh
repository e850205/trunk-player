#! /bin/bash
# trunk-recorder uploadScript for a trunk-player on the same machine.
# Set trunk-recorder's captureDir to this trunk-player's audio_files folder.
# trunk-recorder passes: $1 = .wav, $2 = .json, $3 = .m4a (when compressWav is on)
#-------------------------------------------------------
PLAYER_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

audio="${3:-$1}"
base="${audio%.*}"
audio_dir="$(cd "$(dirname "$audio")" && pwd)"
web_url="${audio_dir#$PLAYER_DIR/audio_files}/"

# trunk-player system for each trunk-recorder shortName (the first folder under audio_files)
short_name="$(echo "$web_url" | cut -d/ -f2)"
case "$short_name" in
  sd-700) SYSTEM=1 ;;
  *) SYSTEM="${TRUNK_PLAYER_SYSTEM:-0}" ;;
esac

type_opt=""
if [ "${audio##*.}" = "m4a" ]; then
  type_opt="--m4a"
  rm -f "$1"  # the m4a is what gets played, drop the wav
fi

cd "$PLAYER_DIR"
env/bin/python manage.py add_transmission "$base" --web_url="$web_url" --system="$SYSTEM" $type_opt
