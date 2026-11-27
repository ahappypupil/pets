# 孩子宠物养成系统

孩子完成奖项赚积分 → 换牛奶/饼干 → 喂宠物 → 破壳/长大/毕业 → 进化成下一阶的蛋。
怪兽会待机动画、主动打招呼、点击发声说话、自我介绍、鼓励打卡；每种怪兽有自己的叫声、爱好和习性，物种数量可无限扩展。

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
| `config/pets.json` | **可扩展宠物目录**：10 种怪兽的配方、山海经出处、爱好、习性、叫声、台词、图形特征 |
| `pet_system/catalog.py` | 目录校验 / 同步到 `pet_species`（老库自动补 `profile_json` 列） |
| `pet_system/domain/rules.py` | R1–R15 规则引擎（纯函数，核心资产） |
| `pet_system/services/` | 奖项/兑换/喂食/配置/账本服务 |
| `pet_system/repo/store.py` | 所有 SQL 集中处 |
| `pet_system/web/templates/` | 孩子端 + 家长端页面 |
| `pet_system/web/static/pets/` | 30 个 SVG 宠物图形（10 种 × 3 形态） |
| `部署指南.md` | **轻量云服务器部署完整步骤**（Nginx + HTTPS + systemd + 备份） |
| `deploy/` | 部署脚本：systemd 服务 / Nginx 配置 / 每日备份 |
| `.env.example` | 服务器配置模板（复制为 `.env` 后填写，不进 git） |
| `tools/gen_pets_svg.py` | 参数化批量生成图形 |
| `tools/verify_ledger.py` | 账本一致性校验 |
| `tests/test_catalog.py` | 目录单测：链完整、档案齐全、图形特征合法 |
| `tools/selftest.py` | 端到端自测（46 项：鉴权/积分/兑换/首阶毕业/说话/配置；有真实数据时默认拒绝运行） |
| `tools/selftest_fullchain.py` | 全链路自测（64 项：10 阶 170 次喂食到终阶毕业/图鉴/异常分支；同样有数据保护） |

## 常用命令

```bash
python -m unittest discover -s tests -v    # 单测 20 项（规则 + 宠物目录）
python tools/selftest.py                   # 端到端自测 46 项（需先启动服务）
python tools/selftest_fullchain.py         # 全链路自测 64 项：10 阶通关
python tools/verify_ledger.py              # 校验余额/库存/图鉴一致
python -m pet_system.catalog               # 同步 config/pets.json 到数据库（新增物种后用）
python -m pet_system.catalog --refresh-profiles  # 只刷新档案/台词/叫声，不改配方
python tools/gen_pets_svg.py               # 重新生成 30 个 SVG
python tools/gen_pets_svg.py --key ember_fox  # 只重生成火苗狐
```

> **数据安全**：两个自测脚本会清空宠物与流水再恢复初始状态。库里已有真实数据时默认**拒绝运行**；确认要在该库上跑时加 `--reset-data`（或设 `PET_SELFTEST_RESET=1`），脚本会先把业务表备份到 `logs/selftest_backup_*.json` 再开始。

## 配置在哪里改

**全部在数据库，家长端「设置 / 奖项管理」界面改即可**，改完即时生效且写审计日志：

- 汇率、库存上限、假期模式、日均目标 → `app_config` 表 / 家长端设置页
- 奖项库 → `award` 表 / 家长端奖项管理页
- 宠物链（名称、配方、次数） → `pet_species` 表
- 怪兽档案与新增物种 → `config/pets.json`（改完执行同步命令）

只有数据库连接信息在 `.env`。

### 新增一种怪兽

1. 在 `config/pets.json` 追加一项：唯一 `id` / `tier`、`svg_key`、`art.features`，以及 `profile`（出处、爱好、习性、`motion`、波形音阶 `voice`、问候语、鼓励语）。
2. 把上一阶的 `next` 改成新 `id`，最后一种保持 `null`；养成链自动按目录重连。
3. 执行 `python -m pet_system.catalog && python tools/gen_pets_svg.py`。
4. 重启服务（或直接调用同步命令）。旧库会自动补 `profile_json` 列，已有配方/次数不会被覆盖。

### 旧数据兼容

- 升级只做「加列 + 加物种」：旧的 `pet_instance`、`codex`、积分/喂食/兑换/领取流水和 `child` 余额都不改动。
- 星辰龙从终阶改为链接九尾狐，只影响**以后**的新蛋；已经毕业或正在养的宠物不受影响。
- `seed.sql` 用显式主键导入初始孩子和蛋，重复执行 `init_db()` 不会产生重复孩子、也不会改掉当前宠物。
- 同步命令只补空档案；家长改过的配方、喂食次数和奖项配置不会被目录覆盖。

## 关键规则

- 1 积分 = 2 份食物；一次喂食 = 当阶配方（牛奶+饼干缺一不可）
- 十阶依次饲养：云团兽(12) → 火苗狐(16) → 星角鹿(20) → 海雾鲸(24) → 星辰龙(30) → 九尾狐(12) → 精卫鸟(12) → 鹿蜀(14) → 旋龟(14) → 白泽(16)
- 后五阶取自《山海经》（青丘九尾狐、精卫、鹿蜀、旋龟、白泽），各有爱好、习性、叫声与鼓励语
- 每阶在 1/3、2/3 处破壳/长大，满次数毕业并自动获得下一阶的蛋
- 怪兽有 5 种待机动画；点击怪兽会用自己的叫声说话，对白用带尖角的漫画对话框弹出；也可点按钮打招呼、自我介绍、获取打卡鼓励
- `/child/api/say?kind=greeting|intro|line|checkin` 分别返回问候、自我介绍（爱好+习性）、随机鼓励语、打卡鼓励语
- 只奖励不惩罚：不扣分、宠物不会饿死、断更不清零、旧宠物永久入图鉴
- 数据库生成列约束保证：同奖项同日不重复领、同时只养一只宠物
- 写请求幂等：连点只生效一次

详见 `宠物养成系统设计.md`（设计）与 `宠物养成系统-架构与实现方案.md`（架构）。

## 上云（可选）

本地跑通后，把 `.env` 的 DB 指向云 MySQL，gunicorn + Nginx + HTTPS 部署即可；`deploy/` 下有参考配置。业务配置已在库里，无需迁移文件。
