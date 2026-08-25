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
-- "reuse this name" check in /review. description is a free-form,
-- always-optional note on what the category is for — purely a text
-- field for the user's own reference, never read by matching/filtering
-- logic anywhere.
--
-- Type is a super-classification one level above the category itself:
-- every category is either an 'Inkomsten' (income) or 'Uitgaven'
-- (expense) category — unrelated to the dashboard's own
-- Inkomsten/Uitgaven totals, which are computed per-transaction from
-- Af_bij, not from this. Deliberately NOT NULL — every category must
-- have one, no "unclassified" limbo state. The app has no UI to choose
-- this at creation time yet (see CHANGELOG), so it defaults to
-- 'Uitgaven' (the more common case) and the user corrects any that are
-- actually 'Inkomsten' afterward via a dedicated endpoint — the DEFAULT
-- exists precisely so that silent fallback never has to fail instead.
-- Not stored on afschrift_subcategorien at all: a subcategory always
-- inherits its parent category's Type by extension (via cat_ID), rather
-- than carrying its own possibly-contradicting value.
create table afschrift_categorien (
	ID integer primary key autoincrement,
	Name varchar(30) not null collate nocase,
	description varchar(500),
	Type varchar(10) not null default 'Uitgaven' check (Type in ('Inkomsten', 'Uitgaven')),
	user_ID integer not null,
	foreign key (user_ID) references Users(ID),
	unique (user_ID, Name)
);

-- Subcategories: scoped to exactly one parent category — a subcategory
-- only exists, and is only ever selectable, under its own cat_ID (this
-- used to be one shared per-user list instead; changed on request, see
-- CHANGELOG). Uniqueness is therefore per-category, not per-user: the
-- same name (e.g. "Overig") can exist once under each of several
-- categories. cat_ID cascades on delete, same as afschrift_cat_regels
-- above — a subcategory has no meaning once its owning category is
-- gone. user_ID is kept alongside cat_ID (redundant with the category's
-- own user_ID) purely for a cheap ownership check without a join, same
-- pattern as afschrift_cat_regel_kolommen.regel_ID/user_ID below. Always
-- optional everywhere it's used (on a regel, on a temp_afschrift/
-- afschrift row) — "no subcategory" is a normal, expected state, never
-- an error. description, like afschrift_categorien's own, is a
-- free-form, always-optional note for the user's own reference.
create table afschrift_subcategorien (
	ID integer primary key autoincrement,
	Name varchar(30) not null collate nocase,
	description varchar(500),
	cat_ID integer not null,
	user_ID integer not null,
	foreign key (cat_ID) references afschrift_categorien(ID) on delete cascade,
	foreign key (user_ID) references Users(ID),
	unique (cat_ID, Name)
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

-- Rule-based categorization: a category is matched by any number of
-- independent "rules" (OR across a category's rules — one row per rule
-- here, cat_ID cascades on delete so removing a category takes its rules
-- with it). See sql/categorization/match_custom_rules.sql for the full
-- matching semantics and docs/ARCHITECTURE.md for the model. Replaces the
-- earlier separate "simple" (Naam) / "difficult" (Mededeling ± paired
-- Naam) / "Interne overboeking" (Tegenrekening-resolves-to-own-account)
-- mechanisms with one general one — a plain Tegenrekening rule against
-- your own IBAN(s) covers what "Interne overboeking" used to do
-- automatically, just explicit and user-owned like everything else here.
create table afschrift_cat_regels (
	ID integer primary key autoincrement,
	cat_ID integer not null,
	subcat_ID integer,
	user_ID integer not null,
	foreign key (cat_ID) references afschrift_categorien(ID) on delete cascade,
	-- SET NULL, not CASCADE: subcat_ID is only one optional field of a
	-- rule, not what defines it (unlike cat_ID) — deleting a subcategory
	-- should just clear it from any rule that assigned it, never delete
	-- the rule (and its category assignment) along with it.
	foreign key (subcat_ID) references afschrift_subcategorien(ID) on delete set null,
	foreign key (user_ID) references Users(ID)
);

-- One row per column a rule places a condition on — a column simply
-- absent from a rule's rows is never checked ("no value = no check").
-- ALL of a rule's columns must match for the rule itself to match (AND
-- across columns, hence the `unique (regel_ID, kolom)` — a rule can only
-- have one condition per column, not two independent ones).
--
-- That COLUMN's own keywords (below) always combine with AND — ALL of
-- them must match simultaneously (only meaningful for substring columns
-- where a field can contain more than one phrase at once, e.g.
-- Mededeling containing both "Salaris" AND "maandelijks" — for a
-- single-valued column like Af_bij, two different keywords can then
-- never match anything, which the app allows rather than blocks; an OR
-- across keywords used to be selectable here too but was removed —
-- express "any of these" as separate rules instead, which OR together
-- via a category's rules above).
--
-- A column-group is expected to always have at least one keyword row
-- (below) — the app deletes a now-empty group rather than leaving it
-- dangling, so an absent row always means "not checked", never "checked
-- against nothing".
create table afschrift_cat_regel_kolommen (
	ID integer primary key autoincrement,
	regel_ID integer not null,
	kolom varchar(20) not null
		check (kolom in ('Naam', 'Tegenrekening', 'Code', 'Af_bij', 'Bedrag_eur',
		                  'Mutatiesoort', 'Mededeling', 'Saldo_na_mutatie', 'Tag')),
	user_ID integer not null,
	foreign key (regel_ID) references afschrift_cat_regels(ID) on delete cascade,
	foreign key (user_ID) references Users(ID),
	unique (regel_ID, kolom)
);

-- The actual keyword/value(s) for one rule's one column-condition.
-- Matching depends on the column's type (see match_custom_rules.sql):
-- LIKE substring for free-text columns (Naam, Tegenrekening, Mededeling,
-- Tag, Mutatiesoort), exact text equality for Code/Af_bij, exact NUMERIC
-- equality (via CAST, not text comparison) for Bedrag_eur/Saldo_na_mutatie
-- — app/categorization_rules.py normalizes/validates a submitted value
-- for its column before it's ever stored here (e.g. Dutch-formatted
-- amounts like '1.234,56' are parsed into a canonical numeric string,
-- Af_bij is restricted to exactly 'Af' or 'Bij').
create table afschrift_cat_regel_keywords (
	ID integer primary key autoincrement,
	regel_kolom_ID integer not null,
	keyword varchar(200) not null,
	user_ID integer not null,
	foreign key (regel_kolom_ID) references afschrift_cat_regel_kolommen(ID) on delete cascade,
	foreign key (user_ID) references Users(ID),
	unique (regel_kolom_ID, keyword)
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
-- reflects only the rule-match outcome (see sql/categorization/):
--   0 = no rule matched — needs a manual category
--   1 = exactly one category matched (by one or more of its rules), eligible for migration
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
	-- No ON DELETE CASCADE/SET NULL on purpose, same reasoning as
	-- Afschrift_cat_ID: a subcategory already referenced by ledger data
	-- must block deletion instead (app-level usage check), never silently
	-- orphan/null out historical rows.
	Afschrift_subcat_ID integer,
	processed integer,
	foreign key (Rekening_ID) references Rekening(ID),
	foreign key (Mutatiesoort_ID) references mutatiesoort(ID),
	foreign key (Afschrift_cat_ID) references afschrift_categorien(ID),
	foreign key (Afschrift_subcat_ID) references afschrift_subcategorien(ID)
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
	-- Same non-cascading FK as temp_afschrift.Afschrift_subcat_ID above —
	-- app-level usage check blocks deleting a subcategory still in use.
	Afschrift_subcat_ID integer,
	foreign key (Rekening_ID) references Rekening(ID),
	foreign key (Mutatiesoort_ID) references mutatiesoort(ID),
	foreign key (Afschrift_cat_ID) references afschrift_categorien(ID),
	foreign key (Afschrift_subcat_ID) references afschrift_subcategorien(ID)
);
