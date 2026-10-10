"""Real cross-subject animation: motion pixels + exact audio/video clocks."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from render import render_lesson
from util import load_json, save_json
from test_pipeline import create_manifest
from scene_fixtures import lesson_fixture


def frame(path, index):
    result = subprocess.run(["ffmpeg","-nostdin","-v","error","-i",str(path),"-vf",f"select=eq(n\\,{index}),scale=480:270",
        "-frames:v","1","-f","rawvideo","-pix_fmt","rgb24","-"],capture_output=True,check=True,timeout=30)
    return np.frombuffer(result.stdout,dtype=np.uint8).reshape(270,480,3)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--fps",type=int,nargs="+",default=[15,30,60])
    args = parser.parse_args()
    root = args.out.resolve()
    root.mkdir(parents=True,exist_ok=True)
    lesson = lesson_fixture()
    save_json(root/"lesson.json",lesson)
    manifest = create_manifest(root,lesson,[192123+i*997 for i in range(len(lesson["segments"]))])
    reports = []
    for fps in args.fps:
        out = root/f"render-{fps}"
        report = render_lesson(root/"lesson.json",out,manifest,quality="l",fps=fps)
        timeline = load_json(out/"timeline.json")
        changes = []
        for segment in timeline["segments"]:
            a = frame(out/"final.mp4",segment["start_frame"]+round(segment["frame_count"]*.15))
            b = frame(out/"final.mp4",segment["start_frame"]+round(segment["frame_count"]*.55))
            # Exclude heading and footer: the diagram body itself must change.
            changed = np.count_nonzero(np.max(np.abs(a.astype(int)-b.astype(int)),axis=2)[65:205,:] > 20)
            if changed < 120:
                raise AssertionError(f"{segment['id']}: no meaningful diagram motion ({changed} pixels)")
            changes.append(int(changed))
        # First two segments deliberately retain one scene. At the boundary,
        # the bodies must retain positions instead of jumping back to origin.
        boundary = timeline["segments"][1]["start_frame"]
        a,b = frame(out/"final.mp4",boundary-1),frame(out/"final.mp4",boundary)
        delta = np.abs(a[75:205].astype(int)-b[75:205].astype(int)).mean()
        if delta > 2:
            raise AssertionError(f"continuation body jumped at the audio boundary: {delta}")
        report["changed_diagram_pixels"] = changes
        report["boundary_mean_pixel_delta"] = float(delta)
        reports.append(report)
    save_json(root/"scene_smoke_results.json",reports)
    print(json.dumps(reports,ensure_ascii=False,indent=2))


if __name__=="__main__": main()
