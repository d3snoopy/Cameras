CREATE TABLE IF NOT EXISTS camUser(
	rowid INTEGER PRIMARY KEY,
	userName TEXT,
	passHash TEXT,
	authLevel INT);

CREATE TABLE IF NOT EXISTS recSettings(
	rowid INTEGER PRIMARY KEY,
	saveLoc TEXT,
	freeTarget INT,
	saveTime INT DEFAULT 60,
	numCam INT,
	lastEdit INT);

CREATE TABLE IF NOT EXISTS camSettings(
	rowid INTEGER PRIMARY KEY,
	name TEXT,
	vidLink TEXT,
	imageLink TEXT);
