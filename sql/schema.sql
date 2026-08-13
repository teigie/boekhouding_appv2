-- Database schema for the boekhouding (accounting) app.
--
-- Order matters: tables are created in dependency order so foreign keys
-- always reference an already-existing table (SQLite doesn't require this,
-- but it keeps the file readable and safe to run with foreign_keys=ON).
--
-- See docs/ARCHITECTURE.md for what each table represents in the pipeline.

-- ---------------------------------------------------------------------------
-- Users & accounts
-- ---------------------------------------------------------------------------

create table Users (
	ID integer primary key autoincrement,
	Name varchar(30),
	creation_date datetime,
	last_logged_in datetime
);

create table Rekening (
	ID integer PRIMARY KEY AUTOINCREMENT,
	name varchar(200) not null UNIQUE,
	creation_date datetime not NULL,
	user_ID integer,
	foreign key (user_ID) references Users(ID)
);

-- ---------------------------------------------------------------------------
-- Reference / lookup tables
-- ---------------------------------------------------------------------------

create table afschrift_categorien (
	ID integer primary key autoincrement,
	Name varchar(30)
);

create table mutatiesoort (
	ID INTEGER PRIMARY KEY AUTOINCREMENT,
	Name varchar(30) not null unique
);

create table mutatiesoort_mapping (
	mutatiesoort_ID integer,
	Name varchar(30) not null unique,
	foreign key (mutatiesoort_ID) references mutatiesoort(ID)
);

create table afschrift_cat_keywords (
	ID integer primary key autoincrement,
	keyword varchar(30) not null unique,
	cat_ID integer,
	foreign key (cat_ID) references afschrift_categorien(ID)
);

-- ---------------------------------------------------------------------------
-- Pipeline: raw upload -> enrichment -> review -> permanent ledger
-- ---------------------------------------------------------------------------

-- Stage 1: raw bank statement rows, exactly as uploaded (no FK resolution).
-- ID is autoincrement and must be treated as the row's original sequence —
-- never reorder these, the running balance depends on it.
create table temp_afschrift2 (
	ID integer primary key autoincrement,
	Datum varchar(8) not null,
	Naam varchar(200) not null,
	Rekening varchar(30) not null,
	Tegenrekening varchar(200),
	Code char(2) not null,
	Af_bij Varchar(3) not null,
	Bedrag_eur dec(10,2) not null,
	Mutatiesoort varchar(30) not null,
	Mededeling Varchar(500),
	Saldo_na_mutatie dec(10,2) not null,
	Tag Varchar(200)
);

-- Stage 2: enrichment output. Same shape as afschrift, plus `processed`:
--   0 = unresolved (missing account/mutatiesoort/category link)
--   1 = cleanly resolved, eligible for migration
--   2 = ambiguous (more than one category keyword matched)
create table temp_afschrift (
	ID integer primary key autoincrement,
	Datum char(10) not null,
	Naam varchar(200) not null,
	Rekening_ID integer not null,
	Tegenrekening varchar(200),
	Code char(2) not null,
	Af_bij Varchar(3) not null,
	Bedrag_eur dec(10,2) not null,
	Mutatiesoort_ID integer not null,
	Mededeling Varchar(500),
	Saldo_na_mutatie dec(10,2) not null,
	Tag Varchar(200),
	Afschrift_cat_ID integer,
	processed integer,
	foreign key (Rekening_ID) references Rekening(ID),
	foreign key (Mutatiesoort_ID) references mutatiesoort(ID),
	foreign key (Afschrift_cat_ID) references afschrift_categorien(ID)
);

-- Stage 3: permanent ledger. Only rows migrated from temp_afschrift once an
-- entire account's pending batch is status 1 land here, in strict sequence.
create table afschrift (
	ID INTEGER PRIMARY KEY AUTOINCREMENT,
	Datum char(10) not null,
	Naam varchar(200) not null,
	Rekening_ID integer not null,
	Tegenrekening varchar(200),
	Code char(2) not null,
	Af_bij Varchar(3) not null,
	Bedrag_eur dec(10,2) not null,
	Mutatiesoort_ID integer not null,
	Mededeling Varchar(500),
	Saldo_na_mutatie dec(10,2) not null,
	Tag Varchar(200),
	Afschrift_cat_ID integer,
	foreign key (Rekening_ID) references Rekening(ID),
	foreign key (Mutatiesoort_ID) references mutatiesoort(ID),
	foreign key (Afschrift_cat_ID) references afschrift_categorien(ID)
);
