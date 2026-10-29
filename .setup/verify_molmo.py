import importlib.util, json
from pathlib import Path
import cv2
from PIL import Image
ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location("molmo_impl",ROOT/"capx/integrations/vision/molmo.py")
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
video=ROOT/"outputs/gpt-6.1-sol/libero_spatial_0_openai_api/trial_01_sandboxrc_0_reward_0.000_taskcompleted_0/video_combined.mp4"
cap=cv2.VideoCapture(str(video));ok,frame=cap.read();cap.release();assert ok
image=Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB))
points=module.init_molmo()(image,["the black bowl between the plate and the ramekin","plate"])
for name,point in points.items():
    assert point[0] is not None and point[1] is not None,(name,point)
    assert 0<=point[0]<image.width and 0<=point[1]<image.height,(name,point)
module._overlay_and_save(image,[(x/image.width*100,y/image.height*100) for x,y in points.values()],str(ROOT/".setup/molmo_verified_points.png"),norm_scale=100.0)
(ROOT/".setup/molmo_points.json").write_text(json.dumps(points,indent=2))
(ROOT/".setup/verify_molmo.exit").write_text("0\n")
print("PASS: Molmo returned in-bounds points for bowl and plate on real LIBERO frame.")
