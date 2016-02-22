<html>
<head>
<link href="../css/dispatcher.css" rel="stylesheet" type="text/css" media="all" />
</head>

<body>
<h2>VPN table - refresh page to update</h2>

<div id="vpn_table">
<?php
	$myfile = fopen("/etc/openvpn/openvpn-status.log", "r") or die("Unable to open file!");
	echo fread($myfile,filesize("/etc/openvpn/openvpn-status.log"));
	fclose($myfile);
?>
</div>

</body>

</html>
