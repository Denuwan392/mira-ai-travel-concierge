"""Local production pipeline. Run .venv/bin/python scripts/demo/production/render.py"""
import hashlib
import json
import math
import re
import shutil
import subprocess as sp
import tempfile
import textwrap
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SRC = ROOT / 'demo-output'
OUT = SRC / 'final'
FPS, RATE = 25, 48000
INK, WHITE, ORANGE, TEAL = '111111', 'FFFFFF', 'F26B1D', '14837B'
PAPER, MUTED = 'FAF9F6', 'B7C4C2'
LOGO = ROOT / 'apps/ceylon-compass/public/logo-mark.png'
FONTS = ROOT / 'apps/ceylon-compass/src/assets/fonts'
VOICE = 'Daniel'


def run(args, **kw):
    return sp.run(list(map(str,args)), check=True, **kw)


def ff(*args, **kw):
    return run(['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-y',*args], **kw)


def probe(path):
    return json.loads(sp.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]))


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()


def stamp(t, srt=False):
    scale = 1000 if srt else 100
    sec, frac = divmod(round(t*scale),scale)
    return f'{sec//3600:02}:{sec//60%60:02}:{sec%60:02}'+(f',{frac:03}' if srt else f'.{frac:02}')


def color(hexval):
    return '&H'+hexval[4:]+hexval[2:4]+hexval[:2]+'&'


class Graphics:
    def __init__(self, duration):
        self.end = duration
        self.events = []

    def event(self, start, end, layer, tags, value):
        if end > start:
            self.events.append(f'Dialogue: {layer},{stamp(start)},{stamp(end)},Type,,0,0,0,,{{{tags}}}{value}')

    def text(self, x,y, value, size, fill=WHITE, start=0, end=None, bold=False, align=7, lift=False, layer=3):
        pos = (rf'\move({x},{y+15},{x},{y},0,380)' if lift else rf'\pos({x},{y})')
        tags = pos+rf'\an{align}\fs{size}\b{int(bold)}\c{color(fill)}\fad(180,90)'
        self.event(start,self.end if end is None else end,layer,tags,value.replace('\n',r'\N'))

    def shape(self, path, fill, start=0, end=None, layer=1, fade=180):
        self.event(start,self.end if end is None else end,layer,
                   rf'\an7\pos(0,0)\p1\bord0\shad0\c{color(fill)}\fad({fade},0)',path)

    def box(self,x,y,w,h,fill,**kw):
        self.shape(f'm {x} {y} l {x+w} {y} {x+w} {y+h} {x} {y+h}',fill,**kw)

    def write(self,p):
        p.write_text('[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\nWrapStyle: 2\nScaledBorderAndShadow: yes\n'
            '[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\n'
            'Style: Type,Inter,34,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1\n'
            '[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'+'\n'.join(self.events)+'\n')


def art(ch):
    g=Graphics(ch['duration'])
    k=ch['key']
    if k.isdigit():
        g.box(112,14,4,22,ORANGE)
        g.text(132,7,k+'   /   '+ch['title'],29,bold=True)
        for i,(s,tag) in enumerate(ch['tags']):
            e=ch['tags'][i+1][0] if i+1<len(ch['tags']) else g.end
            g.text(1806,9,tag,25,'BFDDDA',s,e,align=9)
    elif k in ('opening','closing'):
        g.box(108,144,74,6,ORANGE,start=.12)
        g.text(108,201,'CEYLON COMPASS HOLIDAYS',30,TEAL,start=.24,bold=True,lift=True)
        g.text(96,316,'Meet Mira.' if k=='opening' else 'Mira.',154,INK,start=.62,bold=True,lift=True)
        if k=='opening':
            g.text(109,535,'AI Travel Booking Assistant.',56,INK,start=1.04,lift=True)
            g.text(112,660,'Ceylon Compass Holidays.',36,TEAL,start=1.52,lift=True)
        else:
            for i,label in enumerate(['Grounded Knowledge.','Deterministic Pricing.','Generative UI.','Human Oversight.']):
                g.text(110+(i%2)*520,545+(i//2)*92,label,45,INK,start=.86+i*.32,lift=True)
            g.text(110,792,'Ceylon Compass Holidays',29,TEAL,start=2.2)
    elif k=='architecture':
        g.text(108,85,'SYSTEM ARCHITECTURE',30,'7CC8BE',bold=True)
        g.text(103,160,'From request to trace.',87,WHITE,bold=True,lift=True)
        nodes=[(110,350,'Traveller input','Natural-language request'),(700,350,'LangGraph','Agent orchestration'),
               (1290,350,'Intent processing','Gemini  /  local-rule fallback'),(1290,665,'Business operations','Grounded retrieval + workbook pricing'),
               (700,665,'Validated A2UI','Schema-checked components'),(110,665,'Persistence + tracing','Saved enquiry and correlated events')]
        for i,(x,y,title,desc) in enumerate(nodes):
            t=[.65,1.6,3.1,6,8.4,10][i]
            g.box(x,y,508,185,'23302F',start=t)
            g.box(x,y,5,185,ORANGE if i==3 else TEAL,start=t+.06,layer=2)
            g.text(x+26,y+32,title,43,start=t+.12,bold=True,lift=True)
            g.text(x+26,y+108,desc,26,'C6D7D5',start=t+.19)
            if i in [0,1,3,4]:
                a,b=(x+510,x+581) if i<2 else (x-3,x-75)
                yy=y+92; d=1 if b>a else -1
                g.box(min(a,b),yy,abs(a-b),3,'83B9B2',start=t+.55)
                g.shape(f'm {b} {yy-6} l {b+8*d} {yy+1} {b} {yy+8}', '83B9B2',start=t+.55)
            elif i==2:
                g.box(x+252,y+186,3,118,'83B9B2',start=5)
                g.shape(f'm {x+246} 650 l {x+260} 650 {x+253} 660','83B9B2',start=5)
    else:
        g.text(104,75,'ENGINEERING EVIDENCE',29,TEAL,bold=True)
        g.text(99,148,'Repairing quote state.',78,INK,bold=True,lift=True)
        phases=[('BEFORE','Date mismatch','Quote    3 May 2027\nPicker   10 Jan 2027\nCheckout disabled'),
                ('FIX','One current trip','Hydrate date and party\nRestore route map and photos\nKeep stale-quote checks'),
                ('AFTER','Checkout enabled','2 adults   ·   3 May 2027\nUSD 2,125   /   USD 532 deposit\n7 regression tests passed')]
        for i,(label,title,detail) in enumerate(phases):
            s=0 if i==0 else ch['cues'][i]['local']
            e=ch['cues'][i+1]['local'] if i<2 else g.end
            g.box(108,331,62,5,ORANGE if i<2 else TEAL,start=s,end=e)
            g.text(108,373,label,31,TEAL,s,e,bold=True)
            g.text(106,442,title,49,INK,s,e,bold=True,lift=True)
            g.text(110,555,detail,32,INK,s,e)
    # A dedicated matte keeps captions off the application and all evidence.
    g.box(0,1001,1920,79,INK,layer=5,fade=0)
    for c in ch['cues']:
        wrapped=textwrap.fill(c['text'],width=96,break_long_words=False)
        assert len(wrapped.splitlines())<=2
        g.text(960,1040,wrapped,29,WHITE,c['local'],c['local']+c['length'],align=5,layer=6)
    return g


def narrate(chapters,tmp):
    cursor=0
    for ch in chapters:
        next_time=0
        ch['start']=cursor
        ch['cues']=[]
        for n,(desired,line) in enumerate(ch.pop('lines')):
            aiff=tmp/f"{ch['key']}-{n}.aiff"
            wav=aiff.with_suffix('.wav')
            spoken=line.replace('A2UI','A two U I').replace('98.1','ninety-eight point one').replace('2,125','two thousand one hundred and twenty-five').replace('66,000','sixty-six thousand')
            run(['say','-v',VOICE,'-r','158','-o',aiff,spoken])
            ff('-i',aiff,'-af','silenceremove=start_periods=1:start_threshold=-58dB:start_silence=0.035,afade=t=in:d=0.012','-ar',RATE,'-ac',1,'-c:a','pcm_s16le',wav)
            with wave.open(str(wav)) as w: length=w.getnframes()/RATE
            assert length>.3, 'Local speech service returned empty audio. Run with macOS speech access.'
            local=round(max(desired,next_time),3)
            ch['cues'].append(dict(local=local,start=round(cursor+local,3),length=round(length,4),text=line,wav=wav.name))
            next_time=local+length+.12
        ch['duration']=math.ceil(max(ch['duration'],next_time+.1)*FPS-1e-7)/FPS
        cursor=round(cursor+ch['duration'],2)
    assert 220<=cursor<=255, f'Target edit duration exceeded: {cursor}'
    return cursor


def audio(chapters,tmp,total):
    raw=tmp/'mix.wav'
    with wave.open(str(raw),'wb') as out:
        out.setparams((1,2,RATE,0,'NONE','not compressed'))
        for ch in chapters:
            for cue in ch['cues']:
                gap=round(cue['start']*RATE)-out.getnframes()
                assert gap>=0
                out.writeframes(bytes(gap*2))
                with wave.open(str(tmp/cue['wav'])) as w: out.writeframes(w.readframes(w.getnframes()))
        out.writeframes(bytes((round(total*RATE)-out.getnframes())*2))
    ff('-i',raw,'-af','loudnorm=I=-17:TP=-2:LRA=8','-ar',RATE,'-ac',1,'-c:a','pcm_s24le',OUT/'Mira_Voiceover.wav')


def video(ch,tmp):
    k=ch['key']; dur=ch['duration']; ass=tmp/(k+'.ass')
    art(ch).write(ass)
    args=[]; graph=[]
    if k.isdigit():
        args=['-i',SRC/ch['file']]
        graph.append('[0:v]scale=1696:954:flags=lanczos:out_range=tv:out_color_matrix=bt709,pad=1920:1080:112:46:color=0x111111,setsar=1,tpad=stop_mode=clone:stop_duration=4[base]')
    else:
        bg=INK if k=='architecture' else PAPER
        args=['-f','lavfi','-i',f'color=c=0x{bg}:s=1920x1080:r=25:d={dur}']
        if k in ('opening','closing'):
            args+=['-loop','1','-framerate','25','-i',LOGO]
            graph.append("[1:v]scale=355:-1,format=rgba,fade=t=in:st=0:d=0.48:alpha=1[mark]")
            graph.append("[0:v][mark]overlay=x='1375+15*exp(-5*t)':y=326[base]")
        elif k=='repair':
            for i,name in enumerate(['02-failure','02-journey','02-verified']):
                args+=['-i',SRC/'screenshots'/(name+'.png')]
                crop='crop=1152:890:768:72' if i!=1 else 'crop=1152:932:768:72'
                graph.append(f'[{i+1}:v]{crop},scale=-2:664,pad=1080:680:(ow-iw)/2:8:white[p{i}]')
                t=ch['cues'][i]['local'] if i else 0
                first='0:v' if i==0 else f'b{i-1}'
                last='base' if i==2 else f'b{i}'
                graph.append(f"[{first}][p{i}]overlay=735:268:enable='gte(t,{t})'[{last}]")
        else: graph.append('[0:v]null[base]')
    graph.append(f"[base]ass=filename='{ass}':fontsdir='{FONTS}',format=yuv420p[v]")
    ff(*args,'-filter_complex',';'.join(graph),'-map','[v]','-an','-frames:v',round(dur*FPS),
       '-c:v','libx264','-threads','5','-preset','veryfast','-crf','17','-r',FPS,'-colorspace','bt709',
       '-color_primaries','bt709','-color_trc','bt709',tmp/(k+'.mp4'))
    frames=int(probe(tmp/(k+'.mp4'))['streams'][0]['nb_frames'])
    assert frames==round(dur*FPS),(k,frames,dur)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    chapters=json.loads((HERE/'story.json').read_text())
    source=json.loads((SRC/'timeline.json').read_text())
    hashes={}
    for ch in chapters:
        k=ch['key']
        if k.isdigit():
            record=source[k]
            assert record['status']=='verified'
            ch.update(file=record['file'],duration=record['duration'],source_cue_times=[c['at'] for c in record['cues']])
            hashes[ch['file']]=sha(SRC/ch['file'])
    with tempfile.TemporaryDirectory(prefix='mira-film-',dir='/tmp') as work:
        tmp=Path(work)
        print('Measuring local narration',flush=True)
        total=narrate(chapters,tmp)
        audio(chapters,tmp,total)
        subtitles=[]; script=[]
        for ch in chapters:
            script.extend(['',f"{stamp(ch['start'])}  {ch['title']}"])
            for cue in ch['cues']:
                s=cue['start']; e=s+cue['length']
                subtitles+= [f"{len(subtitles)+1}\n{stamp(s,True)} --> {stamp(e,True)}\n{textwrap.fill(cue['text'],96)}\n"]
                script.append(f"{stamp(s)}  {cue['text']}")
                cue.pop('wav')
        (OUT/'Mira_Subtitles.srt').write_text('\n'.join(subtitles))
        (OUT/'final_narration.txt').write_text('\n'.join(script).strip()+'\n')
        (OUT/'final_timeline.json').write_text(json.dumps(dict(duration=total,fps=FPS,voice=VOICE,chapters=chapters,source_sha256=hashes),indent=2)+'\n')
        for ch in chapters:
            print('Rendering',ch['key'],ch['duration'],flush=True); video(ch,tmp)
        (tmp/'order.txt').write_text(''.join("file '"+ch['key']+".mp4'\n" for ch in chapters))
        dest=OUT/'Mira_Final_Demo.mp4'
        ff('-f','concat','-safe','0','-i',tmp/'order.txt','-i',OUT/'Mira_Voiceover.wav','-map','0:v:0','-map','1:a:0',
           '-c:v','copy','-c:a','aac','-b:a','192k','-ar',RATE,'-movflags','+faststart','-metadata','title=Meet Mira',dest)
        ff('-xerror','-i',dest,'-f','null','-')
        assert hashes=={f:sha(SRC/f) for f in hashes}
        print(f'Complete. {total:.2f} seconds; source hashes verified.',flush=True)

if __name__=='__main__':
    main()
