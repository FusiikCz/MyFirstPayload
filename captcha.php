<?php
/**
 * LAB MOCK CAPTCHA — same scheme as the research sample: four white digits
 * on a green background; the answer is the sum of the first two. Used to test
 * OCR (/solve) and demonstrate why this CAPTCHA is weak (see DEFENSE.md).
 *
 * Requires the PHP GD extension: sudo apt install php-gd
 * LAB ONLY.
 */
session_start();

$d = [];
for ($i = 0; $i < 4; $i++) { $d[] = random_int(0, 9); }
$_SESSION['kod'] = $d[0] + $d[1];

$im = imagecreatetruecolor(100, 30);
$green = imagecolorallocate($im, 40, 140, 60);
$white = imagecolorallocate($im, 255, 255, 255);
$blue  = imagecolorallocate($im, 60, 90, 200);

imagefilledrectangle($im, 0, 0, 99, 29, $green);
for ($i = 0; $i < 6; $i++) {           // noise
    imageline($im, random_int(0, 99), random_int(0, 29),
                    random_int(0, 99), random_int(0, 29), $blue);
}
$x = 14;
foreach ($d as $c) {                   // digits
    imagestring($im, 5, $x, random_int(4, 10), (string)$c, $white);
    $x += 20;
}

header('Content-Type: image/jpeg');
header('Cache-Control: no-store');
imagejpeg($im);
imagedestroy($im);
