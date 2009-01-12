-- Next-generation byCycle schema
--
-- This is intended to be the blueprint for a more general-purpose SQL-based 
-- GIS schema schema [sic], possibly a replacement for shapefiles. A table 
-- starting with "layer_" is (you guessed it!) a layer. It is a lot like a 
-- combined .shp/.dbf. A significant difference is that the attributes can be 
-- normalized (in the RDMS sense) by using additional tables combined with 
-- layer attributes that end in "_i" or "_id". An attribute ending in "_i"
-- points to the sequential index of an attribute in another table. The table 
-- is specifed by naming the attribute with that table name like so: table_i 
-- or f_table_id.
--
-- Attribute naming convention: Prefix_NameOrTableName_Suffix_IOrId
-- When the attribute name ends in "_i" or "_id", the attribute value will be 
-- looked up in the table pointed to by NameOrTableName. When the name ends in 
-- "i" the name will be looked up by index; when it ends in "_id" it will be 
-- looked up by id, where index and id are the names of columns containing,
-- respectively, the sequential index and unique ID for each record.
--
-- The geometry column will contain a binary geometry representation.


DROP TABLE `layer_street`;
CREATE TABLE `layer_street` (
  `index`        INTEGER PRIMARY KEY AUTOINCREMENT,
  `id`           INTEGER NOT NULL,
  `geometry`     BLOB    NOT NULL,
  `wkt_geometry` TEXT    NOT NULL,
  `f_node_id`    INTEGER NOT NULL,
  `t_node_id`    INTEGER NOT NULL,
  `f_addr_l`     INTEGER NOT NULL,
  `t_addr_l`     INTEGER NOT NULL,
  `f_addr_r`     INTEGER NOT NULL,
  `t_addr_r`     INTEGER NOT NULL,
  `streetname_i` INTEGER NOT NULL,
  `city_l_i`     INTEGER NOT NULL,
  `city_r_i`     INTEGER NOT NULL,
  `state_l_i`    INTEGER NOT NULL,
  `state_r_i`    INTEGER NOT NULL,
  `zip_l`        INTEGER NOT NULL,
  `zip_r`        INTEGER NOT NULL
  `one_way`      INTEGER NOT NULL,
  `cfcc`         TEXT    NOT NULL,	
  `bikemode`     TEXT    NOT NULL,
  `grade`        TEXT    NOT NULL,
  `lanes`        INTEGER NOT NULL,	
  `adt`          INTEGER NOT NULL,
  `spd`          INTEGER NOT NULL,
  `feet`         NUMERIC NOT NULL
);

DROP TABLE `layer_node`;
CREATE TABLE `layer_node` (
  `index`        INTEGER PRIMARY KEY AUTOINCREMENT,
  `id`           INTEGER NOT NULL,
  `geometry`     BLOB    NOT NULL,
  `wkt_geometry` TEXT    NOT NULL
);

DROP TABLE `city`;
CREATE TABLE `cities` (
  `index` INTEGER PRIMARY KEY AUTOINCREMENT,
  `city`  TEXT UNIQUE NOT NULL
);

DROP TABLE `matrix`;
CREATE TABLE `matrices` (
  `index`  INTEGER PRIMARY KEY AUTOINCREMENT,
  `mode`   TEXT UNIQUE NOT NULL,
  `matrix` BLOB NOT NULL
);

DROP TABLE `state`;
CREATE TABLE `states` (
  `index` INTEGER PRIMARY KEY AUTOINCREMENT,
  `code`  TEXT UNIQUE NOT NULL,
  `state` TEXT UNIQUE NOT NULL
);

DROP TABLE `streetname`;
CREATE TABLE `streetnames` (
  `index`  INTEGER PRIMARY KEY AUTOINCREMENT,
  `prefix` TEXT NOT NULL,
  `name`   TEXT NOT NULL,
  `type`   TEXT NOT NULL,
  `suffix` TEXT NOT NULL,
  UNIQUE (`prefix`,`name`,`type`,`suffix`)
);

