-- Idempotent copy of the pensioenplanner tables from sql/schema.sql,
-- always executed by app/db.py::init_db() (not only against a brand-new
-- database) — these three tables were added after the app's initial
-- release, so an already-existing data/boekhouding.db never runs
-- schema.sql again and would otherwise never get them. "create table if
-- not exists" makes this a no-op on every run after the first, both for
-- an existing installation and for a brand-new one (where schema.sql
-- already created them moments earlier) — never touches existing data.
--
-- Keep this in sync with the fire_instellingen/fire_personen/fire_posten
-- definitions in sql/schema.sql — see that file for the documentation
-- comments on each column.

create table if not exists fire_instellingen (
	user_ID integer primary key,
	start_jaar integer not null,
	eind_jaar integer not null,
	historie_maanden integer not null default 24,
	algemeen_groei_pct dec(5,2) not null default 0,
	saldo_spaargeld dec(12,2) not null default 0,
	rendement_spaargeld_pct dec(5,2) not null default 0,
	saldo_beleggingen dec(12,2) not null default 0,
	rendement_beleggingen_pct dec(5,2) not null default 0,
	updated_at datetime not null,
	foreign key (user_ID) references Users(ID)
);

create table if not exists fire_personen (
	ID integer primary key autoincrement,
	user_ID integer not null,
	naam varchar(100) not null,
	geboortejaar integer not null,
	foreign key (user_ID) references Users(ID)
);

create table if not exists fire_posten (
	ID integer primary key autoincrement,
	user_ID integer not null,
	omschrijving varchar(200) not null,
	Afschrift_cat_ID integer,
	Afschrift_subcat_ID integer,
	persoon_ID integer,
	type varchar(10) not null check (type in ('Inkomsten', 'Uitgaven')),
	jaarbedrag dec(12,2) not null default 0,
	groei_pct dec(5,2),
	start_jaar integer,
	stop_jaar integer,
	eenmalig integer not null default 0 check (eenmalig in (0, 1)),
	actief integer not null default 1 check (actief in (0, 1)),
	updated_at datetime not null,
	foreign key (user_ID) references Users(ID),
	foreign key (Afschrift_cat_ID) references afschrift_categorien(ID),
	foreign key (Afschrift_subcat_ID) references afschrift_subcategorien(ID),
	foreign key (persoon_ID) references fire_personen(ID) on delete set null
);
