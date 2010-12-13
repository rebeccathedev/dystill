-- Adds a comparison column so we don't just rely on regexp matching.

-- 0 - Starts With
-- 1 - Ends With
-- 2 - Contains
-- 3 - Is 
-- 4 - Regexp

alter table filters add column comparison int(1) not null default 0 after field;