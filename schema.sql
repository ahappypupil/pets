-- 孩子宠物养成系统 · MySQL 8 建表脚本
-- 执行：mysql -u root -p < schema.sql    （或由 pet_system/db.py 读取执行）
-- 说明：只新建 pets 库，不影响机器上其它数据库

CREATE DATABASE IF NOT EXISTS pets DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE pets;

SET FOREIGN_KEY_CHECKS = 0;

-- ============================================================
-- 1. 业务配置（全部配置入库，只有 .env 存 DB 连接信息）
-- ============================================================
CREATE TABLE IF NOT EXISTS app_config (
  config_key   VARCHAR(64) PRIMARY KEY,
  value_json   JSON NOT NULL,
  description  VARCHAR(200) DEFAULT NULL,
  updated_by   VARCHAR(64) DEFAULT NULL,
  updated_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='业务配置：汇率/阈值/假期模式等';

CREATE TABLE IF NOT EXISTS config_audit (
  id         BIGINT AUTO_INCREMENT PRIMARY KEY,
  config_key VARCHAR(64) NOT NULL,
  old_json   JSON DEFAULT NULL,
  new_json   JSON NOT NULL,
  operator   VARCHAR(64) DEFAULT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_audit_key_time (config_key, created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='配置修改审计';

-- ============================================================
-- 2. 账号与孩子
-- ============================================================
CREATE TABLE IF NOT EXISTS admin_user (
  id            BIGINT AUTO_INCREMENT PRIMARY KEY,
  username      VARCHAR(64) NOT NULL UNIQUE,
  password_hash CHAR(64) NOT NULL COMMENT 'pbkdf2_sha256 hex',
  salt          CHAR(32) NOT NULL,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='家长账号';

CREATE TABLE IF NOT EXISTS child (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  name            VARCHAR(32) NOT NULL,
  avatar          VARCHAR(64) DEFAULT NULL,
  pin_hash        CHAR(64) DEFAULT NULL COMMENT '孩子端4位PIN加盐hash',
  salt            CHAR(32) DEFAULT NULL,
  points_balance  INT NOT NULL DEFAULT 0,
  current_pet_id  BIGINT DEFAULT NULL,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CHECK (points_balance >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='孩子档案与积分余额';

-- ============================================================
-- 3. 奖项与领取（R1 用生成列约束：只有 approved 才占每日名额）
-- ============================================================
CREATE TABLE IF NOT EXISTS award (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  name            VARCHAR(64) NOT NULL,
  icon            VARCHAR(64) DEFAULT NULL,
  points          INT NOT NULL,
  daily_cap       INT NOT NULL DEFAULT 1,
  need_approval   TINYINT(1) NOT NULL DEFAULT 1,
  category        VARCHAR(16) NOT NULL DEFAULT '学习',
  exclusive_group VARCHAR(32) DEFAULT NULL,
  enabled         TINYINT(1) NOT NULL DEFAULT 1,
  source_type     VARCHAR(16) NOT NULL DEFAULT 'manual' COMMENT 'manual/auto/external',
  effective_from  DATE DEFAULT NULL,
  effective_to    DATE DEFAULT NULL,
  sort_order      INT NOT NULL DEFAULT 0,
  CHECK (points > 0),
  CHECK (daily_cap > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='奖项库配置';

CREATE TABLE IF NOT EXISTS award_claim (
  id            BIGINT AUTO_INCREMENT PRIMARY KEY,
  child_id      BIGINT NOT NULL,
  award_id      BIGINT NOT NULL,
  claim_date    DATE NOT NULL,
  status        VARCHAR(16) NOT NULL DEFAULT 'pending' COMMENT 'pending/approved/rejected',
  approver_id   BIGINT DEFAULT NULL,
  note          VARCHAR(200) DEFAULT NULL,
  created_at    DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  -- R1：只有 approved 的行生成非 NULL key，NULL 在唯一索引中可重复。
  -- 末尾拼 created_at(微秒)，使 daily_cap>1 的奖项同日可批准多次；
  -- 同一条申请仍只能批准一次（由 UPDATE ... WHERE status='pending' 的 rowcount 保证）。
  approved_key  VARCHAR(160)
      GENERATED ALWAYS AS (
        CASE WHEN status = 'approved'
             THEN CONCAT(child_id, ':', award_id, ':', claim_date, ':', created_at)
             ELSE NULL END
      ) STORED,
  UNIQUE KEY uk_claim_approved (approved_key),
  KEY idx_claim_child_date (child_id, claim_date DESC),
  KEY idx_claim_status (status, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='奖项申请与审核流水';

-- ============================================================
-- 4. 积分账本（只追加，不可删）
-- ============================================================
CREATE TABLE IF NOT EXISTS point_ledger (
  id            BIGINT AUTO_INCREMENT PRIMARY KEY,
  child_id      BIGINT NOT NULL,
  type          VARCHAR(16) NOT NULL COMMENT 'earn/spend/adjust',
  delta         INT NOT NULL,
  balance_after INT NOT NULL,
  ref_type      VARCHAR(32) DEFAULT NULL,
  ref_id        BIGINT DEFAULT NULL,
  operator      VARCHAR(64) DEFAULT NULL,
  note          VARCHAR(200) DEFAULT NULL,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_ledger_child_time (child_id, created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='积分流水（只追加）';

-- ============================================================
-- 5. 兑换与库存
-- ============================================================
CREATE TABLE IF NOT EXISTS exchange_order (
  id            BIGINT AUTO_INCREMENT PRIMARY KEY,
  child_id      BIGINT NOT NULL,
  points_spent  INT NOT NULL,
  milk_qty      INT NOT NULL,
  cookie_qty    INT NOT NULL,
  request_id    VARCHAR(64) NOT NULL,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_exchange_req (request_id),
  KEY idx_exchange_child_time (child_id, created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='兑换单';

CREATE TABLE IF NOT EXISTS food_stock (
  child_id   BIGINT PRIMARY KEY,
  milk       INT NOT NULL DEFAULT 0,
  cookie     INT NOT NULL DEFAULT 0,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CHECK (milk >= 0),
  CHECK (cookie >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='食物库存（冗余，真相源为流水）';

-- ============================================================
-- 6. 宠物链与实例（R14 用生成列约束：同时只有一只在养）
-- ============================================================
CREATE TABLE IF NOT EXISTS pet_species (
  id             BIGINT AUTO_INCREMENT PRIMARY KEY,
  tier           INT NOT NULL,
  name           VARCHAR(32) NOT NULL,
  egg_name       VARCHAR(32) NOT NULL,
  formula_milk   INT NOT NULL,
  formula_cookie INT NOT NULL,
  feed_times     INT NOT NULL COMMENT '本阶毕业所需喂食次数 K',
  next_species_id BIGINT DEFAULT NULL,
  svg_key        VARCHAR(32) NOT NULL COMMENT '对应 SVG 文件名前缀',
  UNIQUE KEY uk_species_tier (tier),
  CHECK (formula_milk > 0),
  CHECK (formula_cookie > 0),
  CHECK (feed_times > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='宠物链配置';

CREATE TABLE IF NOT EXISTS pet_instance (
  id            BIGINT AUTO_INCREMENT PRIMARY KEY,
  child_id      BIGINT NOT NULL,
  species_id    BIGINT NOT NULL,
  status        VARCHAR(16) NOT NULL DEFAULT 'egg' COMMENT 'egg/juvenile/adult/graduated',
  feed_count    INT NOT NULL DEFAULT 0,
  started_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  graduated_at  DATETIME DEFAULT NULL,
  -- R14：只有进行中的宠物生成非 NULL key，一个孩子只能有一只
  active_key    VARCHAR(32)
      GENERATED ALWAYS AS (
        CASE WHEN status IN ('egg','juvenile','adult')
             THEN CAST(child_id AS CHAR) ELSE NULL END
      ) STORED,
  UNIQUE KEY uk_pet_active (active_key),
  KEY idx_pet_child_status (child_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='宠物实例';

CREATE TABLE IF NOT EXISTS feeding_record (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  pet_id          BIGINT NOT NULL,
  child_id        BIGINT NOT NULL,
  milk_used       INT NOT NULL,
  cookie_used     INT NOT NULL,
  feed_count_after INT NOT NULL,
  request_id      VARCHAR(64) NOT NULL,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_feed_req (request_id),
  KEY idx_feed_pet (pet_id, id DESC),
  KEY idx_feed_child_time (child_id, created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='喂食流水';

CREATE TABLE IF NOT EXISTS codex (
  id                BIGINT AUTO_INCREMENT PRIMARY KEY,
  child_id          BIGINT NOT NULL,
  species_id        BIGINT NOT NULL,
  first_graduated_at DATETIME NOT NULL,
  total_feedings    INT NOT NULL,
  milk_used         INT NOT NULL,
  cookie_used       INT NOT NULL,
  certificate_no    VARCHAR(64) NOT NULL,
  UNIQUE KEY uk_codex_child_species (child_id, species_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='宠物图鉴（永久）';

-- ============================================================
-- 7. 幂等与外部事件
-- ============================================================
CREATE TABLE IF NOT EXISTS request_log (
  request_id  VARCHAR(64) PRIMARY KEY,
  result_json JSON DEFAULT NULL,
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='写请求幂等去重';

CREATE TABLE IF NOT EXISTS external_award_event (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  child_id        BIGINT NOT NULL,
  source          VARCHAR(32) NOT NULL,
  external_ref_id VARCHAR(128) NOT NULL,
  points          INT NOT NULL,
  processed       TINYINT(1) NOT NULL DEFAULT 0,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_event_ref (source, external_ref_id),
  KEY idx_event_processed (processed, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='英语工具等外部奖项事件';

SET FOREIGN_KEY_CHECKS = 1;
