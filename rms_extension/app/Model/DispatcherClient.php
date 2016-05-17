/*
Author: Matouš Jezerský

Dispatcher - PHP interface utilizing Dispatcher configuration protocol

*/

<?php

class DispatcherClient extends AppModel {

	public $name = 'DispatcherClient';
	
	public static function getBoundIP() {
		$json = file_get_contents('http://'.Configure::read('VPN_SERVER_IP').'/ext/getData.php');
		if ($json == "ERROR") { return null; }
		$json_data = json_decode($json, true);
		
		if (empty($json_data['payload'])) { return null; }
		$myip = $_SERVER['REMOTE_ADDR']; // can't use IP from JSON, since the request was done by PHP (would show server IP)
		if ( array_key_exists($myip, $json_data['payload']['bindings']) ) {
			return $json_data['payload']['bindings'][$myip];
		}
		return null;
	}
	
	public static function bindIP($clntIP, $serverIP, $bindTime) {
		$ip = "localhost";
		$port = 2107;

		$sock = socket_create(AF_INET, SOCK_STREAM, SOL_TCP);
		if ($sock == false) {
			echo "socket_create error\n";
		}

		if (!socket_connect($sock, $ip, $port)) { throw new InternalErrorException('Dispatcher server offline'); }

		$msg = socket_read($sock, 128);

		$msg = "APP_CLIENT";
		socket_write($sock, $msg, strlen($msg));
		$msg = socket_read($sock, 128);

		$msg = 'B'.$clntIP.'#'.$serverIP.'#'.$bindTime;

		$lenStr = strlen($msg).'#';

		socket_write($sock, $lenStr, strlen($lenStr));
		socket_write($sock, $msg, strlen($msg));

		$msg = socket_read($sock, 128);	
		
		socket_shutdown($sock);
		socket_close($sock);
	}


	public static function bindToMe($serverIP, $bindTime) {
		$client = $_SERVER['REMOTE_ADDR'];
		self::bindIP($client, $serverIP, $bindTime);
	}
	
}

?>
