#!/usr/bin/env python3
"""Generate a sample lab CAPTCHA (in the style of captcha.php) and save it to
/tmp/cap_lab.jpg. Write 'digits=NNNN sum=N' to /tmp/cap_lab.info.

Used by test_c2.sh to verify the /solve OCR endpoint.
LAB ONLY — not for bypassing real-world systems.
"""
import random
from PIL import Image, ImageDraw

d = [random.randint(0, 9) for _ in range(4)]
img = Image.new("RGB", (100, 30), (40, 140, 60))
dr = ImageDraw.Draw(img)
for _ in range(6):
    dr.line([random.randint(0, 99), random.randint(0, 29),
             random.randint(0, 99), random.randint(0, 29)], fill=(60, 90, 200))
x = 14
for c in d:
    dr.text((x, random.randint(4, 10)), str(c), fill=(255, 255, 255))
    x += 20
img.save("/tmp/cap_lab.jpg", "JPEG")

info = "digits={} sum={}".format("".join(map(str, d)), d[0] + d[1])
open("/tmp/cap_lab.info", "w").write(info)
print("  " + info)
