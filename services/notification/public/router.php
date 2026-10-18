<?php
// PHP development-server router; Apache uses FallbackResource in its own config.
$path=parse_url($_SERVER['REQUEST_URI'],PHP_URL_PATH);
$candidate=realpath(__DIR__.$path);
$root=realpath(__DIR__);
if ($path!=='/' && $candidate!==false && str_starts_with($candidate,$root.DIRECTORY_SEPARATOR) && is_file($candidate)) return false;
require __DIR__.'/index.php';
