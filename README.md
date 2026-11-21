# 孩子宠物养成系统

孩子完成奖项赚积分 → 换牛奶/饼干 → 喂宠物 → 破壳/长大/毕业 → 进化成下一阶的蛋。

## 启动（Windows 本地）

**前提**：MySQL 8 已启动，root / 123321（见 `.env`，可改）。

方式一：双击 `启动.bat`（会自动建库并打开服务）。

方式二：命令行：
```bash
python -c "from pet_system.db import init_db; init_db()"   # 首次建库，幂等
python app.py
```
浏览器打开 **http://127.0.0.1:5000**

## 默认账号

| 入口 | 账号 | 密码/PIN |
|---|---|---|
| 孩子端 | 选孩子「宝贝」 | PIN `1234` |
| 家长端 | `admin` | `admin123` |

> 首次登录后请修改默认密码/PIN。

## 目录说明

| 路径 | 内容 |
|---|---|
| `app.py` | 服务入口 |
| `.env` | **唯一本地配置**：DB 连接串、SECRET_KEY |
| `schema.sql` / `config/seed.sql` | 建表 / 首次种子（只在空库导入，不覆盖家长配置） |
| `pet_system/domain/rules.py` | R1–R15 规则引擎（纯函数，核心资产） |
| `pet_system/services/` | 奖项/兑换/喂食/配置/账本服务 |
| `pet_system/repo/store.py` | 所有 SQL 集中处 |
| `pet_system/web/templates/` | 孩子端 + 家长端页面 |
| `pet_system/web/static/pets/` | 15 个 SVG 宠物图形 |
| `部署指南.md` | **轻量云服务器部署完整步骤**（Nginx + HTTPS + systemd + 备份） |
| `deploy/` | 部署脚本：systemd 服务 / Nginx 配置 / 每日备份 |
| `.env.example` | 服务器配置模板（复制为 `.env` 后填写，不进 git） |
| `tools/gen_pets_svg.py` | 参数化批量生成图形 |
| `tools/verify_ledger.py` | 账本一致性校验 |
| `tools/selftest.py` | 端到端自测（41 项：鉴权/积分/兑换/首阶毕业/配置，跑完自动恢复初始数据） |
| `tools/selftest_fullchain.py` | 全链路自测（39 项：5 阶 102 次喂食到终阶毕业/图鉴/异常分支，跑完自动恢复初始数据） |

## 常用命令

```bash
python -m unittest tests.test_rules -v     # 规则单测（9 项）
python tools/selftest.py                   # 端到端自测 41 项（需先启动服务；跑完自动恢复初始数据）
python tools/selftest_fullchain.py         # 全链路自测 39 项：5 阶通关（跑完自动恢复初始数据）
python tools/verify_ledger.py              # 校验余额/库存/图鉴一致
python tools/gen_pets_svg.py               # 重新生成 15 个 SVG
python tools/gen_pets_svg.py --key ember_fox  # 只重生成火苗狐
```

## 配置在哪里改

**全部在数据库，家长端「设置 / 奖项管理」界面改即可**，改完即时生效且写审计日志：

- 汇率、库存上限、假期模式、日均目标 → `app_config` 表 / 家长端设置页
- 奖项库 → `award` 表 / 家长端奖项管理页
- 宠物链（名称、配方、次数） → `pet_species` 表

只有数据库连接信息在 `.env`。

## 关键规则

- 1 积分 = 2 份食物；一次喂食 = 当阶配方（牛奶+饼干缺一不可）
- 五阶依次饲养：云团兽(12次) → 火苗狐(16) → 星角鹿(20) → 海雾鲸(24) → 星辰龙(30)
- 每阶在 1/3、2/3 处破壳/长大，满次数毕业并自动获得下一阶的蛋
- 只奖励不惩罚：不扣分、宠物不会饿死、断更不清零、旧宠物永久入图鉴
- 数据库生成列约束保证：同奖项同日不重复领、同时只养一只宠物
- 写请求幂等：连点只生效一次

详见 `宠物养成系统设计.md`（设计）与 `宠物养成系统-架构与实现方案.md`（架构）。

## 上云（可选）

本地跑通后，把 `.env` 的 DB 指向云 MySQL，gunicorn + Nginx + HTTPS 部署即可；`deploy/` 下有参考配置。业务配置已在库里，无需迁移文件。
