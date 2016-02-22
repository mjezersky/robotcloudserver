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
	
	socket_shutdown($sock);
	socket_close($sock);
}


if (isset($_POST["target"])) {
	$client = $_SERVER['REMOTE_ADDR'];
    $server = htmlspecialchars($_POST["target"]);
	bindIP($client, $server);
}
?>


<html>
<head>
<link href="../css/dispatcher.css" rel="stylesheet" type="text/css" media="all" />
<script src="../js/jquery.min.js"></script>
</head>

<body>
<br>

<div id="dispatcher_content">

</div>

<br>
<form method="POST">
<input id="dispatcher_target" type="text" name="target">
</form>

<script type="text/javascript">
	var dataobj = null;
	var dbg = null;
	
	var interval = null;
	
	function bindTo(eventSource, clientIP) {
		clearInterval(interval);
		eventSource.className += " pressed";
		console.log("binding to "+clientIP);
		dbg = clientIP;
		$.post("", { "target": clientIP });
		interval = setInterval(getJSON, 1000);
		return true;
	}
	
	function refreshContent(data) {
		if (data == "ERROR") {
			$("#dispatcher_content").html('<div class="error">Server unreachable</div>');
			return;
		}
		dataobj = JSON.parse(data);
		
		var tableStr = "<table> <tr> <td>Name</td> <td>Robot IP</td> <td>Bound IPs</td> <td>Time</td> <td>Battery</td> <td>Connection quality</td> <td></td> </tr>";
		
		var payload = dataobj.payload;
		if ("clients" in payload) {
			for (robot in payload.clients) {
				if ("data" in payload.clients[robot]) {
					var boundIPs = "";
					var boundToMe = false;
					
					var robotIP = payload.clients[robot].ip;
					for (b in payload.bindings) {
						if (payload.bindings[b] == robotIP) {
							if (boundIPs != "") { boundIPs += ", "; }
							boundIPs += b;
							if (b == dataobj.ip) { boundToMe = true; }
						}
					}
					if (boundToMe) { 	tableStr += '<tr id="boundToMe"> '; }
					else { 				tableStr += '<tr> '; } 
					tableStr += "<td>" + robot + "</td> ";
					tableStr += "<td>" + robotIP + "</td> ";
					tableStr += "<td>" + boundIPs + "</td> ";
					tableStr += "<td>" + payload.clients[robot].data.time + "</td> ";
					tableStr += "<td>" + payload.clients[robot].data.battery + "</td> ";
					tableStr += "<td>" + payload.clients[robot].rtt + "</td> ";
					if (boundToMe) {	tableStr += '<td> <a href="#" onclick="bindTo(this,' + "''" + ')">Unbind</a> </td> '; }
					else { 				tableStr += '<td> <a href="#" onclick="bindTo(this,'+"'" + robotIP + "'" + ')">Bind</a> </td> '; }
					tableStr += "</tr> ";
				}
			}
			
		}
		else {
			tableStr += "No robots connected";
		}
		tableStr += "</table>";
		
		$("#dispatcher_content").html(tableStr);
	}
	
	function getJSON() {
		$.ajax({url:"/dev/getData.php", success: refreshContent });
	}
	getJSON();
	interval = setInterval(getJSON, 1000);
</script>

</body>

</html>
