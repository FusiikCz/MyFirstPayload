<?php
/**
 * LAB MOCK WEBSITE — vulnerable and patched versions of the same app.
 * Demonstrates a stored XSS/keylogger/worm chain and defense effectiveness.
 *
 *   index.php           -> VULNERABLE (unescaped output, no CSP)
 *   index.php?safe=1    -> PATCHED (htmlspecialchars + CSP header)
 *
 * LAB ONLY. Must not be deployed publicly.
 */
session_start();
$SAFE  = isset($_GET['safe']);
$FILE  = __DIR__ . '/ads.json';
$ads   = file_exists($FILE) ? (json_decode(file_get_contents($FILE), true) ?: []) : [];

$err = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $kod = $_POST['kod'] ?? '';
    $expected = $_SESSION['kod'] ?? null;
    if ($expected === null || $kod === '' || (int)$kod !== (int)$expected) {
        $err = 'Incorrect CAPTCHA code.';
    } else {
        $ads[] = [
            'jmeno' => ($_POST['jmeno'] ?? 'anon'),
            'text'  => ($_POST['TextArea'] ?? ''),
            'ts'    => date('H:i:s'),
        ];
        file_put_contents($FILE, json_encode($ads, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES));
        unset($_SESSION['kod']);
        header('Location: index.php' . ($SAFE ? '?safe=1' : ''));
        exit;
    }
}

if ($SAFE) {
    header("Content-Security-Policy: default-src 'self'; script-src 'self'; "
         . "img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'");
}
?>
<!doctype html>
<meta charset="utf-8">
<title>LAB mock — <?= $SAFE ? 'PATCHED' : 'VULNERABLE' ?></title>
<style>
 body{font:14px sans-serif;background:#f2f2f2;max-width:760px;margin:30px auto}
 .ad{background:#fff;border:1px solid #ccc;padding:10px;margin:8px 0}
 .bad{color:#b00}.good{color:#070}
 form{background:#fff;border:1px solid #ccc;padding:12px;margin-top:20px}
 input,textarea{display:block;margin:6px 0;width:100%}
</style>
<h1>LAB mock website — <?= $SAFE ? '<span class=good>PATCHED (escaped + CSP)</span>' : '<span class=bad>VULNERABLE (raw output)</span>' ?></h1>
<p>The same application in two modes. Enter the test sample in "Text" and compare the behavior.</p>

<?php foreach ($ads as $a): ?>
  <div class="ad">
    <b>Name:</b>
    <?= $SAFE ? htmlspecialchars($a['jmeno'], ENT_QUOTES | ENT_HTML5, 'UTF-8') : $a['jmeno'] ?>
    <br>
    <?= $SAFE ? htmlspecialchars($a['text'], ENT_QUOTES | ENT_HTML5, 'UTF-8') : $a['text'] ?>
  </div>
<?php endforeach; ?>

<form method="post" action="index.php<?= $SAFE ? '?safe=1' : '' ?>">
  <h3>New ad</h3>
  <?php if ($err): ?><p class="bad"><?= htmlspecialchars($err) ?></p><?php endif; ?>
  <input name="jmeno" placeholder="Name" value="LabTester">
  <textarea name="TextArea" rows="5" placeholder="Text (enter test sample here)"></textarea>
  <label>CAPTCHA: <img src="captcha.php" alt="CAPTCHA"
        style="vertical-align:middle;border:1px solid #999"></label>
  <input name="kod" placeholder="sum of the first 2 digits" style="width:180px">
  <button name="button" value="Submit">Submit</button>
</form>
<p><a href="index.php<?= $SAFE ? '' : '?safe=1' ?>">Switch to <?= $SAFE ? 'VULNERABLE' : 'PATCHED' ?> mode</a></p>
