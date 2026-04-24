-- ============================================================
-- seed.sql — reference data only, no user records
-- ============================================================

-- -------------------------
-- Schools
-- -------------------------
insert into schools (id, name, type, canonical_url) values
  ('00000000-0000-0000-0000-000000000001', 'De Anza College',            'CCC',     'https://www.deanza.edu'),
  ('00000000-0000-0000-0000-000000000002', 'UC Davis',                   'UC',      'https://www.ucdavis.edu'),
  ('00000000-0000-0000-0000-000000000003', 'San Jose State University',  'CSU',     'https://www.sjsu.edu')
on conflict (id) do nothing;


-- -------------------------
-- Courses — De Anza College
-- -------------------------
insert into courses (id, school_id, department, number, title, units) values
  ('00000000-0000-0000-0001-000000000001', '00000000-0000-0000-0000-000000000001', 'CIS',  '22A',  'Introduction to Programming', 4),
  ('00000000-0000-0000-0001-000000000002', '00000000-0000-0000-0000-000000000001', 'CIS',  '22B',  'Intermediate Programming',    4),
  ('00000000-0000-0000-0001-000000000003', '00000000-0000-0000-0000-000000000001', 'CIS',  '22C',  'Data Structures',             4),
  ('00000000-0000-0000-0001-000000000004', '00000000-0000-0000-0000-000000000001', 'CIS',  '36A',  'Java Programming',            4),
  ('00000000-0000-0000-0001-000000000005', '00000000-0000-0000-0000-000000000001', 'MATH', '1A',   'Calculus',                    5),
  ('00000000-0000-0000-0001-000000000006', '00000000-0000-0000-0000-000000000001', 'MATH', '1B',   'Calculus II',                 5),
  ('00000000-0000-0000-0001-000000000007', '00000000-0000-0000-0000-000000000001', 'MATH', '1C',   'Calculus III',                5),
  ('00000000-0000-0000-0001-000000000008', '00000000-0000-0000-0000-000000000001', 'MATH', '1D',   'Differential Equations',      5),
  ('00000000-0000-0000-0001-000000000009', '00000000-0000-0000-0000-000000000001', 'MATH', '2A',   'Linear Algebra',              5),
  ('00000000-0000-0000-0001-000000000010', '00000000-0000-0000-0000-000000000001', 'EWRT', '1A',   'Composition and Reading',     5)
on conflict (id) do nothing;


-- -------------------------
-- Articulation agreement: De Anza -> UC Davis, CS, 2024
-- -------------------------
insert into articulation_agreements (id, from_ccc_id, to_school_id, major_name, effective_year) values
  (
    '00000000-0000-0000-0002-000000000001',
    '00000000-0000-0000-0000-000000000001',  -- De Anza
    '00000000-0000-0000-0000-000000000002',  -- UC Davis
    'Computer Science',
    2024
  )
on conflict (id) do nothing;


-- articulation_rows omitted from seed: to_course_id is part of the composite PK
-- and cannot be null. Rows will be inserted once UC Davis course IDs are known.
