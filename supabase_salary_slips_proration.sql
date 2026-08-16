-- Run once in the Supabase SQL Editor for an existing salary_slips table.
alter table public.salary_slips
add column if not exists standard_salary numeric(12,2),
add column if not exists month_working_days integer;

update public.salary_slips
set standard_salary = gross_salary
where standard_salary is null;

update public.salary_slips
set month_working_days = working_days
where month_working_days is null;

alter table public.salary_slips
alter column standard_salary set not null,
alter column month_working_days set not null;
