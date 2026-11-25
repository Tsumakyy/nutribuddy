-- NutriBuddy — dados fictícios para testes
-- ATENÇÃO: apaga TODOS os usuários, pacientes, dietas, check-ins e conversas.
-- A tabela de alimentos (foods) é mantida.
-- Senha de todos os acessos: 123456

USE nutribuddy;
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE buddy_messages;
TRUNCATE TABLE checkins;
TRUNCATE TABLE diet_overrides;
TRUNCATE TABLE diet_items;
TRUNCATE TABLE meal_configs;
TRUNCATE TABLE patients;
TRUNCATE TABLE users;
SET FOREIGN_KEY_CHECKS = 1;

START TRANSACTION;

-- Nutricionista
INSERT INTO users (id, email, password_hash, role, name) VALUES (1, 'nutri@teste.com', '$2b$12$d87fIzdOR2GEvHnWzpCyouJRNFwq1byYTz8IxBr5bPBdQZWv7Vm.m', 'nutritionist', 'Dra. Marina Alves');

-- Paciente 1: Ana Souza — Emagrecimento
INSERT INTO users (id, email, password_hash, role, name) VALUES (2, 'ana@teste.com', '$2b$12$d87fIzdOR2GEvHnWzpCyouJRNFwq1byYTz8IxBr5bPBdQZWv7Vm.m', 'patient', 'Ana Souza');
INSERT INTO patients (id, user_id, nutritionist_id, goal, birth_date, since, bonus_xp) VALUES (1, 2, 1, 'Emagrecimento', '1992-03-14', DATE_SUB(CURDATE(), INTERVAL 30 DAY), 0);
INSERT INTO meal_configs (id, patient_id, meal_key, custom_label, custom_time) VALUES
  (1, 1, 'cafe', 'Café da manhã', '07:00'),
  (2, 1, 'lanche1', 'Lanche da manhã', '10:00'),
  (3, 1, 'almoco', 'Almoço', '12:30'),
  (4, 1, 'lanche2', 'Lanche da tarde', '16:00'),
  (5, 1, 'jantar', 'Jantar', '19:30');
INSERT INTO diet_items (id, patient_id, meal_key, food, qty, position) VALUES
  (1, 1, 'cafe', 'Pão de forma integral', '50g', 0),
  (2, 1, 'cafe', 'Ovo mexido', '100g', 1),
  (3, 1, 'cafe', 'Mamão papaia', '150g', 2),
  (4, 1, 'lanche1', 'Iogurte natural desnatado', '170g', 0),
  (5, 1, 'lanche1', 'Morango', '100g', 1),
  (6, 1, 'almoco', 'Arroz integral', '100g', 0),
  (7, 1, 'almoco', 'Feijão carioca cozido', '80g', 1),
  (8, 1, 'almoco', 'Peito de frango grelhado', '120g', 2),
  (9, 1, 'almoco', 'Brócolis cozido', '80g', 3),
  (10, 1, 'almoco', 'Alface crespa', '40g', 4),
  (11, 1, 'almoco', 'Azeite de oliva', '5g', 5),
  (12, 1, 'lanche2', 'Maçã', '130g', 0),
  (13, 1, 'lanche2', 'Castanha-do-pará', '8g', 1),
  (14, 1, 'jantar', 'Tilápia grelhada', '130g', 0),
  (15, 1, 'jantar', 'Batata-doce cozida', '120g', 1),
  (16, 1, 'jantar', 'Abobrinha cozida', '100g', 2),
  (17, 1, 'jantar', 'Azeite de oliva', '5g', 3);

-- Paciente 2: Bruno Lima — Hipertrofia
INSERT INTO users (id, email, password_hash, role, name) VALUES (3, 'bruno@teste.com', '$2b$12$d87fIzdOR2GEvHnWzpCyouJRNFwq1byYTz8IxBr5bPBdQZWv7Vm.m', 'patient', 'Bruno Lima');
INSERT INTO patients (id, user_id, nutritionist_id, goal, birth_date, since, bonus_xp) VALUES (2, 3, 1, 'Hipertrofia', '1996-07-02', DATE_SUB(CURDATE(), INTERVAL 37 DAY), 150);
INSERT INTO meal_configs (id, patient_id, meal_key, custom_label, custom_time) VALUES
  (6, 2, 'cafe', 'Café da manhã', '07:00'),
  (7, 2, 'almoco', 'Almoço', '12:30'),
  (8, 2, 'lanche2', 'Lanche da tarde', '16:00'),
  (9, 2, 'pre_treino', 'Pré-treino', '17:30'),
  (10, 2, 'pos_treino', 'Pós-treino', '19:00'),
  (11, 2, 'jantar', 'Jantar', '19:30');
INSERT INTO diet_items (id, patient_id, meal_key, food, qty, position) VALUES
  (18, 2, 'cafe', 'Aveia em flocos', '50g', 0),
  (19, 2, 'cafe', 'Banana prata', '100g', 1),
  (20, 2, 'cafe', 'Leite desnatado', '250g', 2),
  (21, 2, 'cafe', 'Pasta de amendoim integral', '15g', 3),
  (22, 2, 'almoco', 'Arroz branco cozido', '200g', 0),
  (23, 2, 'almoco', 'Feijão preto cozido', '100g', 1),
  (24, 2, 'almoco', 'Patinho moído cozido', '150g', 2),
  (25, 2, 'almoco', 'Cenoura cozida', '80g', 3),
  (26, 2, 'almoco', 'Azeite de oliva', '10g', 4),
  (27, 2, 'lanche2', 'Pão de forma integral', '75g', 0),
  (28, 2, 'lanche2', 'Frango desfiado cozido', '80g', 1),
  (29, 2, 'lanche2', 'Requeijão light', '20g', 2),
  (30, 2, 'pre_treino', 'Tapioca (goma hidratada)', '60g', 0),
  (31, 2, 'pre_treino', 'Banana nanica', '100g', 1),
  (32, 2, 'pos_treino', 'Whey protein concentrado', '30g', 0),
  (33, 2, 'pos_treino', 'Leite desnatado', '250g', 1),
  (34, 2, 'jantar', 'Macarrão integral cozido', '180g', 0),
  (35, 2, 'jantar', 'Peito de frango grelhado', '150g', 1),
  (36, 2, 'jantar', 'Brócolis cozido', '100g', 2),
  (37, 2, 'jantar', 'Azeite de oliva', '10g', 3);

-- Paciente 3: Carla Mendes — Reeducação alimentar
INSERT INTO users (id, email, password_hash, role, name) VALUES (4, 'carla@teste.com', '$2b$12$d87fIzdOR2GEvHnWzpCyouJRNFwq1byYTz8IxBr5bPBdQZWv7Vm.m', 'patient', 'Carla Mendes');
INSERT INTO patients (id, user_id, nutritionist_id, goal, birth_date, since, bonus_xp) VALUES (3, 4, 1, 'Reeducação alimentar', '1988-11-20', DATE_SUB(CURDATE(), INTERVAL 44 DAY), 90);
INSERT INTO meal_configs (id, patient_id, meal_key, custom_label, custom_time) VALUES
  (12, 3, 'cafe', 'Café da manhã', '07:00'),
  (13, 3, 'almoco', 'Almoço', '12:30'),
  (14, 3, 'lanche2', 'Lanche da tarde', '16:00'),
  (15, 3, 'jantar', 'Jantar', '19:30');
INSERT INTO diet_items (id, patient_id, meal_key, food, qty, position) VALUES
  (38, 3, 'cafe', 'Cuscuz de milho cozido', '120g', 0),
  (39, 3, 'cafe', 'Ovo cozido', '100g', 1),
  (40, 3, 'cafe', 'Laranja pera', '150g', 2),
  (41, 3, 'almoco', 'Arroz integral', '120g', 0),
  (42, 3, 'almoco', 'Lentilha cozida', '100g', 1),
  (43, 3, 'almoco', 'Alcatra grelhada', '100g', 2),
  (44, 3, 'almoco', 'Tomate', '80g', 3),
  (45, 3, 'almoco', 'Alface crespa', '40g', 4),
  (46, 3, 'lanche2', 'Iogurte natural integral', '170g', 0),
  (47, 3, 'lanche2', 'Aveia em flocos', '20g', 1),
  (48, 3, 'jantar', 'Arroz integral', '80g', 0),
  (49, 3, 'jantar', 'Ovo mexido', '100g', 1),
  (50, 3, 'jantar', 'Cenoura cozida', '80g', 2),
  (51, 3, 'jantar', 'Abobrinha cozida', '80g', 3);

-- Paciente 4: Diego Rocha — Ganho de massa magra
INSERT INTO users (id, email, password_hash, role, name) VALUES (5, 'diego@teste.com', '$2b$12$d87fIzdOR2GEvHnWzpCyouJRNFwq1byYTz8IxBr5bPBdQZWv7Vm.m', 'patient', 'Diego Rocha');
INSERT INTO patients (id, user_id, nutritionist_id, goal, birth_date, since, bonus_xp) VALUES (4, 5, 1, 'Ganho de massa magra', '1999-01-08', DATE_SUB(CURDATE(), INTERVAL 51 DAY), 520);
INSERT INTO meal_configs (id, patient_id, meal_key, custom_label, custom_time) VALUES
  (16, 4, 'cafe', 'Café da manhã', '07:00'),
  (17, 4, 'lanche1', 'Lanche da manhã', '10:00'),
  (18, 4, 'almoco', 'Almoço', '12:30'),
  (19, 4, 'pre_treino', 'Pré-treino', '17:30'),
  (20, 4, 'pos_treino', 'Pós-treino', '19:00'),
  (21, 4, 'jantar', 'Jantar', '19:30');
INSERT INTO diet_items (id, patient_id, meal_key, food, qty, position) VALUES
  (52, 4, 'cafe', 'Pão francês', '100g', 0),
  (53, 4, 'cafe', 'Ovo mexido', '150g', 1),
  (54, 4, 'cafe', 'Queijo minas frescal', '30g', 2),
  (55, 4, 'cafe', 'Banana prata', '100g', 3),
  (56, 4, 'lanche1', 'Iogurte natural integral', '170g', 0),
  (57, 4, 'lanche1', 'Aveia em flocos', '30g', 1),
  (58, 4, 'lanche1', 'Uva Itália', '100g', 2),
  (59, 4, 'almoco', 'Arroz branco cozido', '250g', 0),
  (60, 4, 'almoco', 'Feijão carioca cozido', '140g', 1),
  (61, 4, 'almoco', 'Alcatra grelhada', '160g', 2),
  (62, 4, 'almoco', 'Brócolis cozido', '100g', 3),
  (63, 4, 'almoco', 'Azeite de oliva', '10g', 4),
  (64, 4, 'pre_treino', 'Pão de forma integral', '50g', 0),
  (65, 4, 'pre_treino', 'Pasta de amendoim integral', '20g', 1),
  (66, 4, 'pre_treino', 'Banana nanica', '100g', 2),
  (67, 4, 'pos_treino', 'Whey protein concentrado', '35g', 0),
  (68, 4, 'pos_treino', 'Banana prata', '100g', 1),
  (69, 4, 'jantar', 'Batata inglesa cozida', '300g', 0),
  (70, 4, 'jantar', 'Salmão grelhado', '150g', 1),
  (71, 4, 'jantar', 'Cenoura cozida', '100g', 2);

-- Paciente 5: Elisa Ferreira — Vegetariana — manutenção
INSERT INTO users (id, email, password_hash, role, name) VALUES (6, 'elisa@teste.com', '$2b$12$d87fIzdOR2GEvHnWzpCyouJRNFwq1byYTz8IxBr5bPBdQZWv7Vm.m', 'patient', 'Elisa Ferreira');
INSERT INTO patients (id, user_id, nutritionist_id, goal, birth_date, since, bonus_xp) VALUES (5, 6, 1, 'Vegetariana — manutenção', '1994-05-30', DATE_SUB(CURDATE(), INTERVAL 58 DAY), 230);
INSERT INTO meal_configs (id, patient_id, meal_key, custom_label, custom_time) VALUES
  (22, 5, 'cafe', 'Café da manhã', '07:00'),
  (23, 5, 'lanche1', 'Lanche da manhã', '10:00'),
  (24, 5, 'almoco', 'Almoço', '12:30'),
  (25, 5, 'lanche2', 'Lanche da tarde', '16:00'),
  (26, 5, 'jantar', 'Jantar', '19:30');
INSERT INTO diet_items (id, patient_id, meal_key, food, qty, position) VALUES
  (72, 5, 'cafe', 'Tapioca (goma hidratada)', '60g', 0),
  (73, 5, 'cafe', 'Ricota fresca', '50g', 1),
  (74, 5, 'cafe', 'Morango', '120g', 2),
  (75, 5, 'lanche1', 'Iogurte natural desnatado', '170g', 0),
  (76, 5, 'lanche1', 'Pera', '130g', 1),
  (77, 5, 'almoco', 'Quinoa cozida', '150g', 0),
  (78, 5, 'almoco', 'Grão-de-bico cozido', '100g', 1),
  (79, 5, 'almoco', 'Tofu firme', '120g', 2),
  (80, 5, 'almoco', 'Tomate', '80g', 3),
  (81, 5, 'almoco', 'Alface crespa', '40g', 4),
  (82, 5, 'almoco', 'Azeite de oliva', '10g', 5),
  (83, 5, 'lanche2', 'Homus (pasta de grão-de-bico)', '40g', 0),
  (84, 5, 'lanche2', 'Cenoura cozida', '80g', 1),
  (85, 5, 'jantar', 'Arroz integral', '120g', 0),
  (86, 5, 'jantar', 'Lentilha cozida', '120g', 1),
  (87, 5, 'jantar', 'Ovo cozido', '100g', 2),
  (88, 5, 'jantar', 'Abobrinha cozida', '100g', 3);

-- Paciente 6: Felipe Araújo — Controle de peso
INSERT INTO users (id, email, password_hash, role, name) VALUES (7, 'felipe@teste.com', '$2b$12$d87fIzdOR2GEvHnWzpCyouJRNFwq1byYTz8IxBr5bPBdQZWv7Vm.m', 'patient', 'Felipe Araújo');
INSERT INTO patients (id, user_id, nutritionist_id, goal, birth_date, since, bonus_xp) VALUES (6, 7, 1, 'Controle de peso', '1985-09-17', DATE_SUB(CURDATE(), INTERVAL 65 DAY), 60);
INSERT INTO meal_configs (id, patient_id, meal_key, custom_label, custom_time) VALUES
  (27, 6, 'cafe', 'Café da manhã', '07:00'),
  (28, 6, 'almoco', 'Almoço', '12:30'),
  (29, 6, 'lanche2', 'Lanche da tarde', '16:00'),
  (30, 6, 'jantar', 'Jantar', '19:30');
INSERT INTO diet_items (id, patient_id, meal_key, food, qty, position) VALUES
  (89, 6, 'cafe', 'Pão de forma integral', '50g', 0),
  (90, 6, 'cafe', 'Queijo cottage', '50g', 1),
  (91, 6, 'cafe', 'Melancia', '200g', 2),
  (92, 6, 'almoco', 'Arroz parboilizado cozido', '120g', 0),
  (93, 6, 'almoco', 'Feijão preto cozido', '80g', 1),
  (94, 6, 'almoco', 'Tilápia grelhada', '150g', 2),
  (95, 6, 'almoco', 'Brócolis cozido', '100g', 3),
  (96, 6, 'almoco', 'Azeite de oliva', '5g', 4),
  (97, 6, 'lanche2', 'Iogurte natural desnatado', '170g', 0),
  (98, 6, 'lanche2', 'Mamão papaia', '120g', 1),
  (99, 6, 'jantar', 'Mandioca cozida', '150g', 0),
  (100, 6, 'jantar', 'Frango desfiado cozido', '120g', 1),
  (101, 6, 'jantar', 'Abobrinha cozida', '100g', 2),
  (102, 6, 'jantar', 'Tomate', '60g', 3),
  (103, 6, 'jantar', 'Azeite de oliva', '5g', 4);

-- Paciente 7: Gabriela Nunes — Performance — corrida
INSERT INTO users (id, email, password_hash, role, name) VALUES (8, 'gabriela@teste.com', '$2b$12$d87fIzdOR2GEvHnWzpCyouJRNFwq1byYTz8IxBr5bPBdQZWv7Vm.m', 'patient', 'Gabriela Nunes');
INSERT INTO patients (id, user_id, nutritionist_id, goal, birth_date, since, bonus_xp) VALUES (7, 8, 1, 'Performance — corrida', '1997-12-03', DATE_SUB(CURDATE(), INTERVAL 72 DAY), 340);
INSERT INTO meal_configs (id, patient_id, meal_key, custom_label, custom_time) VALUES
  (31, 7, 'cafe', 'Café da manhã', '07:00'),
  (32, 7, 'almoco', 'Almoço', '12:30'),
  (33, 7, 'pre_treino', 'Pré-treino', '17:30'),
  (34, 7, 'pos_treino', 'Pós-treino', '19:00'),
  (35, 7, 'jantar', 'Jantar', '19:30');
INSERT INTO diet_items (id, patient_id, meal_key, food, qty, position) VALUES
  (104, 7, 'cafe', 'Aveia em flocos', '40g', 0),
  (105, 7, 'cafe', 'Leite semidesnatado', '200g', 1),
  (106, 7, 'cafe', 'Banana nanica', '100g', 2),
  (107, 7, 'cafe', 'Morango', '80g', 3),
  (108, 7, 'almoco', 'Macarrão integral cozido', '160g', 0),
  (109, 7, 'almoco', 'Patinho moído cozido', '110g', 1),
  (110, 7, 'almoco', 'Tomate', '100g', 2),
  (111, 7, 'almoco', 'Brócolis cozido', '80g', 3),
  (112, 7, 'almoco', 'Azeite de oliva', '8g', 4),
  (113, 7, 'pre_treino', 'Tapioca (goma hidratada)', '50g', 0),
  (114, 7, 'pre_treino', 'Banana prata', '100g', 1),
  (115, 7, 'pos_treino', 'Iogurte natural integral', '170g', 0),
  (116, 7, 'pos_treino', 'Uva Itália', '100g', 1),
  (117, 7, 'pos_treino', 'Aveia em flocos', '20g', 2),
  (118, 7, 'jantar', 'Batata-doce cozida', '180g', 0),
  (119, 7, 'jantar', 'Salmão grelhado', '120g', 1),
  (120, 7, 'jantar', 'Alface crespa', '50g', 2),
  (121, 7, 'jantar', 'Cenoura cozida', '80g', 3);

-- Paciente 8: Henrique Castro — Saúde cardiovascular
INSERT INTO users (id, email, password_hash, role, name) VALUES (9, 'henrique@teste.com', '$2b$12$d87fIzdOR2GEvHnWzpCyouJRNFwq1byYTz8IxBr5bPBdQZWv7Vm.m', 'patient', 'Henrique Castro');
INSERT INTO patients (id, user_id, nutritionist_id, goal, birth_date, since, bonus_xp) VALUES (8, 9, 1, 'Saúde cardiovascular', '1970-04-25', DATE_SUB(CURDATE(), INTERVAL 79 DAY), 410);
INSERT INTO meal_configs (id, patient_id, meal_key, custom_label, custom_time) VALUES
  (36, 8, 'cafe', 'Café da manhã', '07:00'),
  (37, 8, 'lanche1', 'Lanche da manhã', '10:00'),
  (38, 8, 'almoco', 'Almoço', '12:30'),
  (39, 8, 'lanche2', 'Lanche da tarde', '16:00'),
  (40, 8, 'jantar', 'Jantar', '19:30');
INSERT INTO diet_items (id, patient_id, meal_key, food, qty, position) VALUES
  (122, 8, 'cafe', 'Aveia em flocos', '30g', 0),
  (123, 8, 'cafe', 'Leite desnatado', '200g', 1),
  (124, 8, 'cafe', 'Mamão papaia', '150g', 2),
  (125, 8, 'lanche1', 'Maçã', '130g', 0),
  (126, 8, 'lanche1', 'Castanha-do-pará', '8g', 1),
  (127, 8, 'almoco', 'Arroz integral', '120g', 0),
  (128, 8, 'almoco', 'Feijão carioca cozido', '100g', 1),
  (129, 8, 'almoco', 'Salmão grelhado', '120g', 2),
  (130, 8, 'almoco', 'Brócolis cozido', '100g', 3),
  (131, 8, 'almoco', 'Azeite de oliva', '8g', 4),
  (132, 8, 'lanche2', 'Iogurte natural desnatado', '170g', 0),
  (133, 8, 'lanche2', 'Morango', '100g', 1),
  (134, 8, 'jantar', 'Quinoa cozida', '120g', 0),
  (135, 8, 'jantar', 'Atum em água escorrido', '100g', 1),
  (136, 8, 'jantar', 'Tomate', '80g', 2),
  (137, 8, 'jantar', 'Alface crespa', '50g', 3),
  (138, 8, 'jantar', 'Azeite de oliva', '5g', 4);

-- Paciente 9: Isabela Martins — Emagrecimento
INSERT INTO users (id, email, password_hash, role, name) VALUES (10, 'isabela@teste.com', '$2b$12$d87fIzdOR2GEvHnWzpCyouJRNFwq1byYTz8IxBr5bPBdQZWv7Vm.m', 'patient', 'Isabela Martins');
INSERT INTO patients (id, user_id, nutritionist_id, goal, birth_date, since, bonus_xp) VALUES (9, 10, 1, 'Emagrecimento', '2000-08-11', DATE_SUB(CURDATE(), INTERVAL 86 DAY), 20);
INSERT INTO meal_configs (id, patient_id, meal_key, custom_label, custom_time) VALUES
  (41, 9, 'cafe', 'Café da manhã', '07:00'),
  (42, 9, 'lanche1', 'Lanche da manhã', '10:00'),
  (43, 9, 'almoco', 'Almoço', '12:30'),
  (44, 9, 'lanche2', 'Lanche da tarde', '16:00'),
  (45, 9, 'jantar', 'Jantar', '19:30');
INSERT INTO diet_items (id, patient_id, meal_key, food, qty, position) VALUES
  (139, 9, 'cafe', 'Pão de forma integral', '50g', 0),
  (140, 9, 'cafe', 'Ricota fresca', '40g', 1),
  (141, 9, 'cafe', 'Morango', '100g', 2),
  (142, 9, 'lanche1', 'Pera', '130g', 0),
  (143, 9, 'lanche1', 'Castanha-do-pará', '8g', 1),
  (144, 9, 'almoco', 'Arroz integral', '120g', 0),
  (145, 9, 'almoco', 'Feijão preto cozido', '80g', 1),
  (146, 9, 'almoco', 'Peito de frango grelhado', '110g', 2),
  (147, 9, 'almoco', 'Cenoura cozida', '80g', 3),
  (148, 9, 'almoco', 'Alface crespa', '40g', 4),
  (149, 9, 'almoco', 'Azeite de oliva', '5g', 5),
  (150, 9, 'lanche2', 'Iogurte natural desnatado', '170g', 0),
  (151, 9, 'lanche2', 'Aveia em flocos', '15g', 1),
  (152, 9, 'jantar', 'Clara de ovo cozida', '120g', 0),
  (153, 9, 'jantar', 'Ovo cozido', '50g', 1),
  (154, 9, 'jantar', 'Batata inglesa cozida', '200g', 2),
  (155, 9, 'jantar', 'Abobrinha cozida', '100g', 3),
  (156, 9, 'jantar', 'Azeite de oliva', '5g', 4);

-- Paciente 10: João Pereira — Hipertrofia
INSERT INTO users (id, email, password_hash, role, name) VALUES (11, 'joao@teste.com', '$2b$12$d87fIzdOR2GEvHnWzpCyouJRNFwq1byYTz8IxBr5bPBdQZWv7Vm.m', 'patient', 'João Pereira');
INSERT INTO patients (id, user_id, nutritionist_id, goal, birth_date, since, bonus_xp) VALUES (10, 11, 1, 'Hipertrofia', '1993-02-19', DATE_SUB(CURDATE(), INTERVAL 93 DAY), 600);
INSERT INTO meal_configs (id, patient_id, meal_key, custom_label, custom_time) VALUES
  (46, 10, 'cafe', 'Café da manhã', '07:00'),
  (47, 10, 'lanche1', 'Lanche da manhã', '10:00'),
  (48, 10, 'almoco', 'Almoço', '12:30'),
  (49, 10, 'pre_treino', 'Pré-treino', '17:30'),
  (50, 10, 'pos_treino', 'Pós-treino', '19:00'),
  (51, 10, 'jantar', 'Jantar', '19:30');
INSERT INTO diet_items (id, patient_id, meal_key, food, qty, position) VALUES
  (157, 10, 'cafe', 'Pão francês', '100g', 0),
  (158, 10, 'cafe', 'Ovo cozido', '150g', 1),
  (159, 10, 'cafe', 'Queijo mussarela', '20g', 2),
  (160, 10, 'cafe', 'Laranja pera', '150g', 3),
  (161, 10, 'lanche1', 'Iogurte natural integral', '170g', 0),
  (162, 10, 'lanche1', 'Banana prata', '100g', 1),
  (163, 10, 'lanche1', 'Aveia em flocos', '30g', 2),
  (164, 10, 'almoco', 'Arroz branco cozido', '220g', 0),
  (165, 10, 'almoco', 'Feijão carioca cozido', '140g', 1),
  (166, 10, 'almoco', 'Peito de frango grelhado', '170g', 2),
  (167, 10, 'almoco', 'Brócolis cozido', '100g', 3),
  (168, 10, 'almoco', 'Azeite de oliva', '10g', 4),
  (169, 10, 'pre_treino', 'Batata-doce cozida', '150g', 0),
  (170, 10, 'pre_treino', 'Frango desfiado cozido', '80g', 1),
  (171, 10, 'pos_treino', 'Whey protein concentrado', '30g', 0),
  (172, 10, 'pos_treino', 'Banana nanica', '100g', 1),
  (173, 10, 'jantar', 'Arroz integral', '150g', 0),
  (174, 10, 'jantar', 'Alcatra grelhada', '150g', 1),
  (175, 10, 'jantar', 'Abacate', '60g', 2),
  (176, 10, 'jantar', 'Tomate', '80g', 3);

COMMIT;
