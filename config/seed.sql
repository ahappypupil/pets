-- 孩子宠物养成系统 · 首次初始化种子数据
-- 仅在空库时导入一次；家长后续在界面上改配置，重启不会覆盖
USE pets;

-- 默认业务配置
INSERT IGNORE INTO app_config (config_key, value_json, description) VALUES
  ('exchange_rate',   JSON_OBJECT('rate', 2),                    '1积分可兑换的食物份数'),
  ('stock_cap',       JSON_OBJECT('cap', 99),                    '每种食物库存上限'),
  ('form_thresholds', JSON_OBJECT('t1', 3, 't2', 3),             '形态阈值分母：T1=ceil(K/3), T2=ceil(2K/3)，分母=3'),
  ('holiday_mode',    JSON_OBJECT('enabled', false),             '假期模式：暂停发分但不冻结宠物'),
  ('daily_target',    JSON_OBJECT('points', 15),                 '家长参考的日均积分目标，不展示给孩子'),
  ('pet_svg_version', JSON_OBJECT('version', 'v1'),              'SVG图形版本');

-- 默认家长账号：admin / admin123（首次登录后建议修改）
INSERT IGNORE INTO admin_user (username, password_hash, salt) VALUES
  ('admin', 'c2e71362baddb2bdb8e232eb96e264a9fb8595d5083b3034e3fff8a6fe7bbba5', 'petsalt0000000000000000000000001');

-- 默认孩子：宝贝，PIN=1234（salt 必须正好 32 位，CHAR(32) 会截断）
INSERT IGNORE INTO child (name, avatar, pin_hash, salt, points_balance) VALUES
  ('宝贝', 'cloud_beast', 'aafb27103e0b13c65556cf710e3a5a755cd8d9cb842a21a05f498fd93dee6b84', 'pinsalt0000000000000000000000000', 0);

-- 库存初始行（孩子 id=1）
INSERT IGNORE INTO food_stock (child_id, milk, cookie) VALUES (1, 0, 0);

-- 五阶宠物链（配方与次数对应设计文档第 5.3 节）
INSERT IGNORE INTO pet_species (id, tier, name, egg_name, formula_milk, formula_cookie, feed_times, next_species_id, svg_key) VALUES
  (1, 1, '云团兽', '棉花蛋', 1, 1, 12, 2, 'cloud_beast'),
  (2, 2, '火苗狐', '暖焰蛋', 2, 1, 16, 3, 'ember_fox'),
  (3, 3, '星角鹿', '星屑蛋', 2, 2, 20, 4, 'star_deer'),
  (4, 4, '海雾鲸', '潮汐蛋', 3, 2, 24, 5, 'mist_whale'),
  (5, 5, '星辰龙', '星河蛋', 3, 3, 30, NULL, 'star_dragon');

-- 第一只宠物：云团兽的蛋（孩子 id=1）
INSERT IGNORE INTO pet_instance (child_id, species_id, status, feed_count) VALUES (1, 1, 'egg', 0);
UPDATE child SET current_pet_id = LAST_INSERT_ID() WHERE id = 1 AND current_pet_id IS NULL;

-- 默认奖项库（对应设计文档第 3.2 节）
INSERT IGNORE INTO award (id, name, icon, points, daily_cap, need_approval, category, exclusive_group, enabled, source_type, sort_order) VALUES
  (1,  '按时完成作业',   '📘', 10, 1, 1, '学习', 'homework', 1, 'manual', 1),
  (2,  '作业自查并订正', '✅',  5, 1, 1, '学习', NULL,       1, 'manual', 2),
  (3,  '阅读20分钟',     '📖',  8, 2, 1, '学习', NULL,       1, 'manual', 3),
  (4,  '英语练习1组',    '🔤',  8, 2, 0, '学习', NULL,       1, 'auto',   4),
  (5,  '自己整理书包',   '🎒',  5, 1, 0, '生活', NULL,       1, 'manual', 5),
  (6,  '按时上床睡觉',   '🌙',  5, 1, 1, '生活', NULL,       1, 'manual', 6),
  (7,  '练琴/运动20分钟','🎹', 10, 1, 1, '生活', NULL,       1, 'manual', 7),
  (8,  '主动帮忙做家务', '🧹',  5, 2, 1, '品德', NULL,       1, 'manual', 8),
  (9,  '主动承认错误/说谢谢','💛', 3, 2, 1, '品德', NULL,    1, 'manual', 9),
  (10, '周末特别挑战',   '🏆', 20, 1, 1, '额外', NULL,       1, 'manual', 10);
