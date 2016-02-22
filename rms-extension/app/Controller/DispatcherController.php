<?php

class DispatcherController extends AppController {
	public $uses = array('User', 'Role');

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
	
	public function admin_index() {
		$this->Auth->allow("logo");
	}

}

?>
