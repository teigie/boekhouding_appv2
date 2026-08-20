-- Add a new subcategory, owned by a user. One shared list, not scoped to
-- any single category (see sql/schema.sql).
-- Params: :name, :user_id

insert into afschrift_subcategorien (Name, user_ID) values (:name, :user_id);
