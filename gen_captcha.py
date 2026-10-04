#!/usr/bin/env python3
"""Vygeneruje ukázkovou lab captchu (styl lab/captcha.php) a zapíše ji do
/tmp/cap_lab.jpg. Do /tmp/cap_lab.info uloží 'digits=NNNN sum=N'.

Používá se v lab/test_c2.sh k ověření OCR endpointu /solve.
LAB ONLY — neslouží k žádnému obcházení reálných systémů.
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
