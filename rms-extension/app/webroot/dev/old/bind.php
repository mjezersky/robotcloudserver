<?php
function bindIP($clntIP, $serverIP) {
	$ip = "localhost";
	$port = 2107;

	$sock = socket_create(AF_INET, SOCK_STREAM, SOL_TCP);
	if ($sock == false) {
		echo "socket_create error\n";
	}

	socket_connect($sock, $ip, $port);

	$msg = socket_read($sock, 128);

	$msg = "APP_CLIENT";
	socket_write($sock, $msg, strlen($msg));
	$msg = socket_read($sock, 128);

	$msg = 'B'.$clntIP.'#'.$serverIP;
	echo $msg;

	$lenStr = strlen($msg).'#';

	socket_write($sock, $lenStr, strlen($lenStr));
	socket_write($sock, $msg, strlen($msg));

	$msg = socket_read($sock, 128);
}


if (isset($_POST["target"])) {
	$client = $_SERVER['REMOTE_ADDR'];
        $server = htmlspecialchars($_POST["target"]);
	bindIP($client, $server);
}
?>


<html>
<head>
</head>

<body>
<form method="POST">
<input type="text" name="target">
</form>

</body>

</html>
