-- Params: :id, :user_id

DELETE FROM fire_posten WHERE ID = :id AND user_ID = :user_id;
