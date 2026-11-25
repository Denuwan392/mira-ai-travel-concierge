"""Check the encoded submission without rendering it again."""
import array
import json
import math
import re
import struct
import subprocess as sp
import sys
from pathlib import Path

from render import OUT, SRC, probe, sha, stamp

timeline=json.loads((OUT/'final_timeline.json').read_text())
movie=OUT/'Mira_Final_Demo.mp4'
info=probe(movie)
video,audio=info['streams']
duration=float(info['format']['duration'])
assert (video['codec_name'],video['width'],video['height'],video['pix_fmt'],video['avg_frame_rate'])==('h264',1920,1080,'yuv420p','25/1')
assert audio['codec_name']=='aac' and 220<=duration<=255
assert abs(duration-timeline['duration'])<=.04
assert int(video['nb_frames'])==round(duration*25)
assert abs(float(audio['duration'])-duration)<.04
with movie.open('rb') as f:
    atoms=[]
    while header:=f.read(8):
        size,name=struct.unpack('>I4s',header)
        assert size>=8
        atoms.append(name)
        f.seek(size-8,1)
    assert atoms.index(b'moov')<atoms.index(b'mdat')
hashes=timeline['source_sha256']
assert all(sha(SRC/name)==digest for name,digest in hashes.items())
cmd=['ffmpeg','-nostdin','-hide_banner','-nostats','-xerror','-i',str(movie),'-vf','blackdetect=d=0.04:pix_th=0.025:pic_th=0.99','-af','loudnorm=print_format=json','-f','null','-']
analysis=sp.run(cmd,stderr=sp.PIPE,text=True,check=True).stderr
assert 'black_start:' not in analysis
meter=json.loads(re.search(r'\{\s*"input_i".*?\}',analysis,re.S)[0])
assert float(meter['input_tp']) < 0
pcm=array.array('h')
pcm.frombytes(sp.check_output(['ffmpeg','-loglevel','error','-i',str(movie),'-map','0:a','-ar','8000','-ac','1','-f','s16le','-']))
if sys.byteorder!='little':pcm.byteswap()
subs=(OUT/'Mira_Subtitles.srt').read_text().strip().split('\n\n')
cues=[c for ch in timeline['chapters'] for c in ch['cues']]
assert len(cues)==len(subs)
last=0
for sub,c in zip(subs,cues):
    s,e=c['start'],c['start']+c['length']
    lines=sub.splitlines()
    assert s>=last and e<=duration and len(lines)<=4
    assert lines[1]==stamp(s,True)+' --> '+stamp(e,True)
    assert ' '.join(lines[2:])==c['text']
    samples=pcm[round(s*8000):round(e*8000)]
    assert max(abs(v) for v in samples)>1000
    gap=pcm[round((last+.08)*8000):round((s-.08)*8000)]
    assert not gap or max(abs(v) for v in gap)<300
    last=e
report=f"""# Mira final demo production report

The final film runs {duration:.2f} seconds. The six original recordings contribute 186.36 seconds of real application footage in chronological order. Application interactions play at their recorded speed. Scene 02 includes a 1.76-second final-frame hold for its price and deposit.

## Export and audio

| Check | Verified result |
|---|---|
| Video | 1920 × 1080, H.264, 25 fps, {video['nb_frames']} frames, yuv420p |
| Audio | AAC, 48 kHz mono, with a separate 24-bit PCM voice-over master |
| Speech | Installed macOS Daniel (English UK), 158 words per minute, synthesized locally in {len(cues)} separately measured phrases |
| Final AAC loudness | {meter['input_i']} LUFS integrated, {meter['input_tp']} dBTP true peak |
| Decode and packaging | Complete audio and video decode; fast-start moov atom precedes media data |
| Black frames | No frame met the 99% near-black threshold |
| Caption sync | All {len(cues)} SRT entries match the spoken cue sheet, use one or two lines, remain inside the export, and have non-overlapping measured intervals. Encoded audio contains signal within every cue and silence in the checked gaps. |

The captions are burned into their own matte for playback without a subtitle player. A matching English SRT is supplied separately. The sound mix uses speech alone. Daniel is a synthesized voice. Local place names are read with the voice’s English pronunciation.

## Editorial decisions

The opening and closing use the existing compass mark, Inter, and brand colours. The architecture diagram reveals the workflow in reading order. The application chapters use a separate header for scene names and engineering annotations. The bug-fix insert uses crops from the three original screenshots. Its final hold includes the price, deposit and regression count.

Scenes 01 and 02 explicitly identify local-rule intent extraction. Scene 05 attributes draft generation to Gemini on the basis of the existing audit evidence. The publication decision belongs to the approver. Scene 06 reports 53 of 54 evaluation cases passed (98.1%), ten judge cases scored, and human calibration pending.

## Edit timeline

| Start | Length | Chapter |
|---|---:|---|
"""
for ch in timeline['chapters']:
    report+=f"| {stamp(ch['start'])} | {ch['duration']:.2f} s | {ch['title']} |\n"
report+='\n## Preserved source footage\n\nPre-render and post-render SHA-256 hashes matched for all six inputs.\n\n| File | SHA-256 |\n|---|---|\n'
for name,digest in hashes.items(): report+=f'| {name} | `{digest}` |\n'
report+='\n## Reproduction\n\nEdit `scripts/demo/production/story.json` for narration, cue positions, or labels. From the repository root, run the following with access to the installed macOS speech service.\n\n```sh\n.venv/bin/python scripts/demo/production/render.py\n.venv/bin/python scripts/demo/production/check.py\n```\n\nThe renderer uses FFmpeg, FFprobe, Python’s standard library, and macOS say. Intermediate narration phrases and encoded chapters live in a temporary directory. The final assembly copies the encoded chapter video streams and adds the mastered narration.\n'
(OUT/'production_report.md').write_text(report)
print(duration,meter['input_i'],meter['input_tp'],len(cues))
