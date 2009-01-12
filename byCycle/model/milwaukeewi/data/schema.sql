-- Next-generation byCycle schema (using SQLite syntax)
--
-- This is intended to be the blueprint for a more general-purpose SQL-based 
-- GIS schema schema [sic], possibly a replacement for shapefiles. A table 
-- starting with "layer_" is (you guessed it!) a layer. It is a lot like a 
-- combined .shp/.dbf. A significant difference is that the attributes can be 
-- normalized (in the RDMS sense) by using additional tables combined with 
-- layer attributes that end with "_id" (i.e., foreign keys).
--
-- Attribute naming conventions: 
--     * TableName[_OtherQualifiers]_id
--     * FieldName[_OtherQualifiers]
-- When the attribute name ends with "_id", the attribute value will
-- be looked up in the table pointed to by TableName. The Other Qualifiers part
-- of the attribute name can be anything that is useful for the user's purpose.
--
-- The geometry column will contain a binary geometry representation.

USE `bycycle-1`;

CREATE TABLE `milwaukeewi_layer_street` (
  `id`            INTEGER PRIMARY KEY NOT NULL AUTO_INCREMENT,
  `geom`          LINESTRING NOT NULL,
  -- Attributes all regions should have
  `node_f_id`     INTEGER UNSIGNED NOT NULL,
  `node_t_id`     INTEGER UNSIGNED NOT NULL,
  `addr_f`        MEDIUMINT UNSIGNED NOT NULL,
  `addr_t`        MEDIUMINT UNSIGNED NOT NULL,
  `even_side`     ENUM('l', 'r') NOT NULL,
  `streetname_id` INTEGER NOT NULL,
  `city_l_id`     INTEGER NOT NULL,
  `city_r_id`     INTEGER NOT NULL,
  `state_l_id`    CHAR(2) NOT NULL,
  `state_r_id`    CHAR(2) NOT NULL,
  `zip_l`         MEDIUMINT(5) NOT NULL,
  `zip_r`         MEDIUMINT(5) NOT NULL,
  -- Region-specific attributes
  `one_way`       ENUM('', 'ft', 'tf', 'n') NOT NULL,
  `code`          CHAR(3) NOT NULL,	
  `bikemode`      ENUM('', 't', 'r', 'l', 'p'),
  `lanes`         TINYINT NULL,	
  `adt`           INTEGER NOT NULL,
  `spd`           TINYINT NOT NULL,
  SPATIAL INDEX (`geom`),
  INDEX (`node_f_id`),
  INDEX (`node_t_id`),
  INDEX (`addr_f`),
  INDEX (`addr_t`),
  INDEX (`streetname_id`),
  INDEX (`city_l_id`),
  INDEX (`city_r_id`),
  INDEX (`state_l_id`),
  INDEX (`state_r_id`),
  INDEX (`zip_l`),
  INDEX (`zip_r`)
);

CREATE TABLE `milwaukeewi_layer_node` (
  `id`   INTEGER PRIMARY KEY NOT NULL,
  `geom` POINT NOT NULL,
  SPATIAL INDEX (`geom`)
);

CREATE TABLE `milwaukeewi_streetname` (
  `id`     INTEGER PRIMARY KEY NOT NULL AUTO_INCREMENT,
  `prefix` CHAR(2) NOT NULL,
  `name`   VARCHAR(255) NOT NULL,
  `type`   CHAR(4) NOT NULL,
  `suffix` CHAR(2) NOT NULL,
  INDEX (`prefix`),
  INDEX (`name`),
  INDEX (`type`),
  INDEX (`suffix`)
);

CREATE TABLE `milwaukeewi_city` (
  `id`    INTEGER PRIMARY KEY NOT NULL AUTO_INCREMENT,
  `city`  VARCHAR(255) NOT NULL,
  INDEX (`city`)	
);

CREATE TABLE `milwaukeewi_state` (
  `id`    CHAR(2) PRIMARY KEY NOT NULL, 
  `state` VARCHAR(255) NOT NULL,
  INDEX (`state`)	
);
