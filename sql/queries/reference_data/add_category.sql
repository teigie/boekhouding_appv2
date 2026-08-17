-- Add a new spending category, owned by a user.
-- Params: :name, :user_id

insert into afschrift_categorien (Name, user_ID) values (:name, :user_id);
