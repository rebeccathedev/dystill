-- Purposely breaks the association between Postfix and Dystill. Updates
-- your filters table to use email addresses instead of IDs.

alter table filters add column email varchar(255) not null after filter_id;
update filters inner join users on (user_id = id) set filters.email = users.email;
alter table filters drop column user_id;