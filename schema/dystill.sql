CREATE TABLE `filters` (
  `filter_id` int(11) NOT NULL AUTO_INCREMENT,
  `email` varchar(255) NOT NULL DEFAULT '',
  `field` varchar(50) NOT NULL,
  `comparison` int(1) NOT NULL DEFAULT '0',
  `value` varchar(255) NOT NULL,
  `active` int(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`filter_id`),
  KEY `user_id` (`user_id`)
);

CREATE TABLE `filters_actions` (
  `filter_id` int(11) DEFAULT NULL,
  `action` varchar(10) NOT NULL,
  `argument` varchar(255) NOT NULL,
  PRIMARY KEY (`action_id`),
  KEY `filter_id` (`filter_id`)
);