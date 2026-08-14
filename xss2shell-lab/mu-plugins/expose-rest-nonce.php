<?php
// Lab helper: espone wpApiSettings (nonce REST) sulla pagina di login
// e aggiunge un endpoint REST che restituisce il nonce corrente in JSONP.
add_action( 'login_enqueue_scripts', function() {
    wp_enqueue_script( 'wp-api-request' );
} );

add_action( 'rest_api_init', function() {
    register_rest_route( 'xss2shell/v1', '/nonce', array(
        'methods'  => 'GET',
        'callback' => function() {
            return array(
                'nonce' => wp_create_nonce( 'wp_rest' ),
                'user_id' => get_current_user_id(),
                'logged_in' => is_user_logged_in(),
            );
        },
        'permission_callback' => '__return_true',
    ) );
} );
