<?php
/**
 * Plugin Name: SEO Autopilot – REST Meta Bridge
 * Description: Exposes Yoast / Rank Math SEO meta keys to the WordPress REST API so SEO Autopilot can safely preview and apply updates.
 * Version: 1.0.0
 * Author: SEO Autopilot AI
 *
 * Install: copy to wp-content/mu-plugins/seo-autopilot-meta-bridge.php
 * or wp-content/plugins/ and activate.
 *
 * Security: only users who can edit_posts may write these fields via REST.
 */

add_action( 'init', function () {
	$types = array( 'post', 'page' );
	$keys  = array(
		// Yoast
		'_yoast_wpseo_title',
		'_yoast_wpseo_metadesc',
		'_yoast_wpseo_focuskw',
		'_yoast_wpseo_canonical',
		// Rank Math
		'rank_math_title',
		'rank_math_description',
		'rank_math_focus_keyword',
		'rank_math_canonical_url',
	);

	foreach ( $types as $type ) {
		foreach ( $keys as $key ) {
			register_post_meta(
				$type,
				$key,
				array(
					'type'              => 'string',
					'single'            => true,
					'show_in_rest'      => true,
					'sanitize_callback' => 'sanitize_text_field',
					'auth_callback'     => function () {
						return current_user_can( 'edit_posts' );
					},
				)
			);
		}
	}
} );
