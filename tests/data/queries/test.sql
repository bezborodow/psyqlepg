-- #create
drop table if exists test;
create table test (
    id serial primary key,
    num integer,
    data text
);

-- #get
select *
from test
where id = %s;
