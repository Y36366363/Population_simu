"""Create GIF/MP4 from PNG frames when optional local encoders are available."""
from __future__ import annotations
import argparse, subprocess
from pathlib import Path

def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("frames",type=Path); p.add_argument("--output",type=Path,required=True); p.add_argument("--fps",type=int,default=5); a=p.parse_args()
    frames=sorted(a.frames.glob("*.png"));
    if not frames: raise SystemExit("no_png_frames")
    a.output.parent.mkdir(parents=True,exist_ok=True)
    if a.output.suffix.lower()==".gif":
        try:
            from PIL import Image
        except ImportError: raise SystemExit("GIF requires Pillow: python3 -m pip install pillow")
        images=[Image.open(f).convert("RGB") for f in frames]; images[0].save(a.output,save_all=True,append_images=images[1:],duration=max(1,1000//a.fps),loop=0); print(f"wrote {a.output} frames={len(frames)}"); return 0
    if a.output.suffix.lower()==".mp4":
        cmd=["ffmpeg","-y","-framerate",str(a.fps),"-pattern_type","glob","-i",str(a.frames/"*.png"),"-c:v","libx264","-pix_fmt","yuv420p",str(a.output)]
        try: subprocess.run(cmd,check=True)
        except FileNotFoundError: raise SystemExit("MP4 requires ffmpeg")
        print(f"wrote {a.output} frames={len(frames)}"); return 0
    raise SystemExit("output must end in .gif or .mp4")
if __name__=="__main__": raise SystemExit(main())
