CREATE TABLE IF NOT EXISTS `accounts.users` (
 `user_id` bigint(20) unsigned NOT NULL,
 `email` mediumtext COLLATE utf8mb4_unicode_ci NOT NULL,
 `full_name` mediumtext COLLATE utf8mb4_unicode_ci NOT NULL,
 `profile_pic` mediumtext COLLATE utf8mb4_unicode_ci NOT NULL,
 `registered_on` date NOT NULL,
 UNIQUE KEY `user_id` (`user_id`),
 UNIQUE KEY `email` (`email`(200))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE IF NOT EXISTS `organizations` (
 `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
 `owner_id` bigint(20) unsigned NOT NULL,
 `handle` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
 `title` varchar(120) COLLATE utf8mb4_unicode_ci NOT NULL,
 `type` varchar(4) NOT NULL,
 `email` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
 `phone` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
 `address` mediumtext COLLATE utf8mb4_unicode_ci NOT NULL,
 `city` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
 `country` varchar(2) NOT NULL,
 PRIMARY KEY `id` (`id`),
 UNIQUE KEY `handle` (`handle`),
 FOREIGN KEY `owner_id` (`owner_id`) REFERENCES `accounts.users`(`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;