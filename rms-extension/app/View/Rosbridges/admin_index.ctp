<?php
/**
 * Admin rosbridge Index View
 *
 * The rosbridge index page displays a list of all rosbridge servers in the database. An admin may edit, add, or delete
 * from this list.
 *
 * @author		Russell Toris - rctoris@wpi.edu
 * @copyright	2014 Worcester Polytechnic Institute
 * @link		https://github.com/WPI-RAIL/rms
 * @since		RMS v 2.0.0
 * @version		2.0.9
 * @package		app.View.Rosbridges
 */
?>

<header class="special container">
	<span class="icon fa-gear"></span>
	<h2>rosbridge Servers</h2>
</header>

<section class="wrapper style4 container">
	<div class="content center">
		<section>
			<header>
				<p>
					rosbridge provides a JSON interface to ROS, allowing any client to send JSON to publish or subscribe
					to ROS topics, call ROS services, and more.
				</p>
			</header>
			<?php echo $this->Html->link('Create New Entry', array('action' => 'add'), array('class' => 'button')); ?>
			<br /><br />
			
			<table> <tr>
				<td>Bound rosbridge status</td>
				<?php
					$found = false;
					foreach ($rosbridges as $rosbridge) {
						if ($rosbridge['Rosbridge']['host'] == $bound_ip) {
							echo '<td>';
							echo $this->Html->link(
								__(
									'%s://%s:%s',
									h($rosbridge['Protocol']['name']),
									Configure::read('VPN_SERVER_IP'),
									h($rosbridge['Rosbridge']['port'])
								),
								array('action' => 'view', $rosbridge['Rosbridge']['id'])
							);
							echo '</td> <td data-title="Status">';
							echo $this->Rms->rosbridgeStatus(
								$rosbridge['Protocol']['name'],
								Configure::read('VPN_SERVER_IP'),
								$rosbridge['Rosbridge']['port']
							);							
							echo '</td>';
							$found = true;
							break;
						}
					}
					if (!$found) {
						echo '<td>N/A</td><td>N/A</td>';
					}
				?>
				</td>
			</tr> </table>
			
			<table>
				<tr>
					<th></th>
					<th>ID</th>
					<th>Name</th>
					<th>IP</th>
					<th>rosauth Key</th>
					<th><?php echo $this->Html->link('Environments', array('controller' => 'environments')); ?></th>
				</tr>
				<?php foreach ($rosbridges as $rosbridge): ?>
					<tr>
						<td>
							<?php
							echo $this->Form->postLink(
								'',
								array('action' => 'delete', $rosbridge['Rosbridge']['id']),
								array('class' => 'icon fa-trash-o', 'confirm' => 'Are you sure?')
							);
							?>
							<?php
							echo $this->Html->link(
								'',
								array('action' => 'edit', $rosbridge['Rosbridge']['id']),
								array('class' => 'icon fa-edit')
							);
							?>
						</td>
						<td data-title="ID">
							<?php echo h($rosbridge['Rosbridge']['id']); ?>
						</td>
						<td data-title="Name">
							<?php echo h($rosbridge['Rosbridge']['name']); ?>
						</td>
						<td data-title="IP">
							<?php
							echo h($rosbridge['Rosbridge']['host']);
							?>
						</td>
						
						<td data-title="rosauth Key">
							<?php
							echo ($rosbridge['Rosbridge']['rosauth']) ? h($rosbridge['Rosbridge']['rosauth']) : 'N/A';
							?>
						</td>
						<td data-title="Environments">
							<?php echo count($rosbridge['Environment']); ?>
						</td>
					</tr>
				<?php endforeach; ?>
			</table>
		</section>
	</div>
</section>
