<?php

class DispatcherController extends AppController {

	public $helpers = array('Html', 'Paginator', 'Time', 'Rms');
	public $uses = array('User', 'Role', 'Iface', 'Study', 'Appointment', 'Slot', 'Environment');

	public $components = array(
		'Paginator',
		'Session',
		'Auth' => array(
			'authorize' => 'Controller',
			'loginRedirect' => array('controller' => 'dispatcher', 'action' => 'view'),
			'logoutRedirect' => array('controller' => 'pages', 'action' => 'view'),
			'authenticate' => array(
				'Form' => array('passwordHasher' => array('className' => 'Simple', 'hashType' => 'sha256'))
			)
		)
	);	

	public function beforeFilter() {
		// only allow unauthenticated account creation
		parent::beforeFilter();
		$this->Auth->allow('signup', 'login', 'username', 'reset');
	}

	public function admin_vpn() {
		$this->Auth->allow("logo");
	}
	
	public function index() {
		$this->Auth->allow("logo");
		// find the ID
		$id = $this->Auth->user('id');
		// grab the entry
		$user = $this->User->findById($id);
		if (!$user) {
			// no valid entry found for the given ID
			throw new NotFoundException('Invalid user.');
		}
		// search for interfaces
		if ($this->viewVars['admin']) {
			$this->set('ifaces', $this->Iface->find('all', array('recursive' => 3)));
		} else {
			// only show the unrestricted interfaces
			$ifaces = $this->Iface->find(
				'all',
				array('conditions' => array('Iface.unrestricted' => 1), 'recursive' => 3)
			);
			$this->set('ifaces', $ifaces);
		}
		// search for studies
		$studies = $this->Study->find(
			'all',
			array(
				'recursive' => 3,
				'conditions' => array('Study.start <= CURDATE()', 'Study.end >= CURDATE()')
			)
		);
		$this->set('studies', $studies);
		// do NOT attempt to load all of the logs
		$this->Appointment->hasMany = array();
		$appointments = $this->Appointment->find(
			'all',
			array(
				'recursive' => 3,
				'conditions' => array(
					'Appointment.user_id' => $id,
					'Slot.end >= NOW()',
					'Slot.end < "2038-01-18 22:14:07"'
				),
				'order' => array('Slot.start'),
			)
		);
		$allAppointments = $this->Appointment->find(
			'all',
			array(
				'recursive' => 3,
				'conditions' => array('Appointment.user_id' => $id, 'Slot.end < "2038-01-18 22:14:07"'),
				'order' => array('Slot.start'),
			)
		);		
		
		// === parovani slotu a environmentu ===
		
		$environments = $this->Environment->find('all');
		$environList = array();
		foreach($environments as $env) {
			$environList[$env['Environment']['id']] = $env['Rosbridge']['host'];
		}
		//$this->set('environments', $environList);
		
		$slots = $this->Slot->find('all');
		$slotList = array();
		foreach($slots as $slot) {
			$slotList[$slot['Slot']['id']] = $environList[$slot['Condition']['environment_id']];
		}
		
		
		if (count($appointments)>0) {
			if (strtotime($appointments[0]['Slot']['start']) <=  strtotime('now') && strtotime($appointments[0]['Slot']['end']) > strtotime('now')) {
				$currAppointmentIP = $slotList[$appointments[0]['Slot']['id']];
			}
		}
		else { $currAppointmentIP = "none"; }
		
		$this->set('currAppointmentIP', $currAppointmentIP);
		
		$this->loadModel('DispatcherClient');
		
		if (isset($_POST["target"])) {
			$client = $_SERVER['REMOTE_ADDR'];
			$server = htmlspecialchars($_POST["target"]);
			$bindTime = strtotime($appointments[0]['Slot']['end']) - strtotime('now');
			if ($currAppointmentIP == $server || $server == "") { $this->DispatcherClient->bindIP($client, $server, $bindTime); }
		}

		$this->set('boundip', $this->DispatcherClient->getBoundIP());
	}
	
	public function admin_index() {
		$this->Auth->allow("logo");
		
		$this->loadModel('DispatcherClient');
		
		if (isset($_POST["target"])) {
			$client = $_SERVER['REMOTE_ADDR'];
			$server = htmlspecialchars($_POST["target"]);
			$this->DispatcherClient->bindIP($client, $server, 86400); // admin bind 24h
		}
	}

}

?>
