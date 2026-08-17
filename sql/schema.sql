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

-- Spending categories are per-user, same isolation pattern as Rekening:
-- each user builds and owns their own list, independent of everyone
-- else's. Name's case-insensitive collation makes the (user_ID, Name)
-- uniqueness constraint itself case-insensitive, matching the app-level
-- "reuse this name" check in /review.
create table afschrift_categorien (
	ID integer primary key autoincrement,
	Name varchar(30) not null collate nocase,
	user_ID integer not null,
	foreign key (user_ID) references Users(ID),
	unique (user_ID, Name)
);

-- Global, NOT user-scoped: a fixed list of category names offered as
-- one-click "suggestion" chips on /categories for new/empty users. Never
-- inserted into any user's afschrift_categorien automatically, and never
-- joined into categorization matching — purely a UI template list.
create table afschrift_categorie_suggesties (
	ID integer primary key autoincrement,
	Name varchar(30) not null unique
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

-- "Simple" categorization: substrings of Naam (the counterparty/merchant
-- name) that auto-assign a category, e.g. "Lidl" -> Levensmiddelen.
-- Per-user like afschrift_categorien itself — cat_ID cascades on delete
-- so removing a category takes its keywords with it.
create table afschrift_cat_keywords (
	ID integer primary key autoincrement,
	keyword varchar(30) not null,
	cat_ID integer not null,
	user_ID integer not null,
	foreign key (cat_ID) references afschrift_categorien(ID) on delete cascade,
	foreign key (user_ID) references Users(ID),
	unique (user_ID, keyword)
);

-- "Difficult" categorization: substrings of Mededeling (the free-text
-- transaction description), checked in addition to afschrift_cat_keywords
-- when Naam alone isn't conclusive. Wider than a merchant name, so this
-- allows longer phrases/sentences, not just single words. Per-user, same
-- shape as afschrift_cat_keywords above.
--
-- naam_keyword is an OPTIONAL paired condition: when set, a match
-- requires BOTH `keyword` in Mededeling AND naam_keyword in Naam — e.g.
-- Mededeling keyword "Vakantiegeld" paired with Naam keyword "vakantie",
-- so the combination is precise even though neither substring alone
-- would be. When left NULL, behaves exactly like before: Mededeling
-- alone is enough. This is what extends "difficult" categorization with
-- the same substring-matching idea "simple" categorization already uses
-- for Naam, without requiring a second, separate simple keyword to exist.
create table afschrift_cat_mededeling_keywords (
	ID integer primary key autoincrement,
	keyword varchar(200) not null,
	naam_keyword varchar(30),
	cat_ID integer not null,
	user_ID integer not null,
	foreign key (cat_ID) references afschrift_categorien(ID) on delete cascade,
	foreign key (user_ID) references Users(ID),
	unique (user_ID, keyword)
);

-- ---------------------------------------------------------------------------
-- Pipeline: raw upload -> categorization -> review -> permanent ledger
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

-- Stage 2: categorization output. Same shape as afschrift, plus `processed`.
-- Rekening_ID/Mutatiesoort_ID are resolved independently of `processed` —
-- they're always expected to map (see docs/ARCHITECTURE.md). `processed`
-- reflects only the category-keyword match outcome (Naam + Mededeling
-- combined, see sql/categorization/):
--   0 = no category keyword matched — needs a manual category
--   1 = exactly one category matched, eligible for migration
--   2 = ambiguous — more than one category matched, needs a manual pick
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
