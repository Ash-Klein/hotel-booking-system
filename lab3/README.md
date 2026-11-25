# 云栖酒店预订管理系统（实验三）

软件工程课程实验三：把实验二的 UML 设计实现为可运行代码，并用单元测试、代码风格检查和 Git 管理交付。

- 学号：241220053
- 姓名：黄若希
- 技术栈：Python 3.12 + Tkinter + SQLite（仅标准库，无第三方运行时依赖）
- 源代码规模：约 1.26 万有效行（`python tools/check_style.py` 统计，含测试）
- 测试：`unittest` 32 项，覆盖库存、并发防超卖、状态机、取消退款、改单、履约、权限、审计与报表

## 1. 运行

客人端和员工端是两个**独立程序**，分别启动：

```powershell
cd lab3

# 客人端：390×844 竖屏手机预订
python run_guest.py

# 员工端：门店 / 集团桌面工作台
python run.py
```

首次运行会自动创建 `data/hotel.db`，写入 6 家门店、18 个房型、45 天库存/价格、5 个员工账号和 6 笔演示订单。无需安装依赖。两个程序共享同一个数据库，但窗口、入口、导航完全独立。

如需使用全新数据库：

```powershell
Remove-Item data\hotel.db -Force -ErrorAction SilentlyContinue
python run_guest.py   # 或 python run.py
```

也可以指定数据库路径：

```powershell
python run_guest.py --db data/my_demo.db
python run.py --db data/my_demo.db
```

## 2. 演示账号

| 角色 | 账号 | 密码 | 数据范围 |
|---|---|---|---|
| 门店前台 | `frontdesk` | `Frontdesk@123` | 云栖外滩酒店 |
| 门店店长 | `manager` | `Manager@123` | 外滩店、静安店 |
| 集团财务 | `finance` | `Finance@123` | 全部门店，可审退款/裁决异常 |
| 集团运营 | `admin` | `Admin@123` | 全部门店，可配置特殊日期 |
| 城市经理 | `city` | `City@123` | 上海 3 店，只读 |

客人端不需要登录，直接启动 `run_guest.py`；员工端登录页没有客人端入口。

## 3. 功能范围

### 客人端（独立竖屏客户端）

- 390×844 竖屏窗口，1:1 复刻实验二 UI 稿的 6 屏：01 首页选店、02 选房型、02A 房型详情、03 填单锁房、04 支付、05 订单改退；底部“首页/订单/我的”三 Tab
- 城市 → 门店 → 日期/人数 → 房型 的决策顺序；房型列表只比较房型与起价，间数与总价留到 02A
- 02A 选间数、看价格明细（单价 × 晚数 × 间数）、确认下单后进入 15 分钟锁房倒计时
- 03 登记入住人（多间房可添加入住人）与到店时间，倒计时内去支付；超时锁房释放并阻止提交
- 04 微信/支付宝/银行卡三种支付渠道，订单摘要与金额同屏核对，倒计时与订单 `expire_at` 一致
- 05 订单进度时间轴、取消规则与违约金、自助改期/改房型/同城改店、取消并查看退款
- 手机号查询订单；金额、库存、时长全部来自服务层真实报价，不写死演示数据

### 门店端

- 今日工作台：到店、离店、在住、待支付、可售、当日收款；一键办理入住/退房
- 订单办理：订单号/手机号/姓名检索，确认现付单、入住分房、退房、标记异常、No-show
- 库存与房价：按日查看总量/已售/订单锁定/协议锁定/可售，改价、关房、库存修正、房型停售
- 协议锁房：创建、到期自动释放、提前释放
- 退款审核：>500 元按首晚成交价进入店长审批，≤500 元自动通过
- 操作日志：按操作类型、订单号查询，CSV 导出

### 集团端

- 集团总览：门店数、订单、营收、平均出租率、待审退款、未结异常、近 7 天趋势
- 经营报表：门店/城市维度订单量、间夜、营收、取消率、出租率、ADR，房型销量 Top 5，CSV 导出
- 退款审核、异常台账裁决、全平台审计日志、门店与房型状态管理

## 4. 从 UML 到代码的映射

| 实验二 UML | 实现位置 | 说明 |
|---|---|---|
| `Hotel / RoomType` | `domain/models.py`、`repositories/catalog_repository.py` | 门店与房型主数据 |
| `DailyInventory` | `domain/models.py`、`repositories/inventory_repository.py` | 唯一键 + `available` 不变式；条件 UPDATE 防超卖 |
| `DailyPrice / RoomClosure / GroupLock` | 同上 | 每日价格、关房、协议锁房分表持久化 |
| `Guest / Order / OrderItem` | `domain/models.py`、`services/booking_service.py` | 一单一房型，多间房由 OrderItem 记录 |
| `Payment / Refund` | `domain/models.py`、`services/refund_service.py` | 退款审批以首晚成交价为阈值 |
| UML note 中支撑实体 | `domain/models.py` | Staff、OperationLog、OrderChange、Cancellation、ExceptionRecord、Room |
| 订单状态机 | `domain/enums.py::ORDER_TRANSITIONS` | 只允许白名单转换，其余抛 `StateTransitionError` |
| 应用服务 | `services/` | 认证、查询报价、预订交易、履约、库存管理、退款、报表 |
| 仓储 | `repositories/` | SQL 集中在仓储层，服务层不拼 SQL |
| 表现层 | `ui/` | 独立竖屏客人端、员工登录、门店端、集团端 |

完整实现类图见 `UML/UML实现类图.puml`，实验二核心类图见 `UML/UML类图.puml`。

## 5. 目录

```
lab3/
├── run_guest.py                # 客人端启动脚本（独立竖屏程序）
├── run.py                      # 员工端启动脚本（门店/集团）
├── hotel_booking/
│   ├── domain/                 # 实体、枚举、金额/脱敏、领域异常
│   ├── infrastructure/         # SQLite、Schema、种子数据、密码哈希
│   ├── repositories/           # 7 个仓储 + 行映射
│   ├── services/               # 7 个应用服务 + 组合根 + 演示数据
│   └── ui/
│       ├── mobile_guest.py     # 390×844 客人端页面与底部导航
│       ├── login_view.py       # 员工登录（无客人端入口）
│       ├── staff_view.py       # 门店端
│       └── admin_view.py       # 集团端
├── tests/test_booking.py       # 29 项 unittest
├── tools/check_style.py        # 项目内代码风格检查
├── tools/capture_screens.py    # 报告截图生成（开发辅助）
├── UML/                        # 类图 puml/png
├── report/                     # 报告源文与截图
└── docs/                       # 大模型使用记录
```

## 6. 测试与检查

```powershell
# 单元测试
$env:PYTHONPATH="."
python -m unittest discover -s tests -v

# 代码风格（100 列、行尾空白、制表符、文档、裸 except）
python tools/check_style.py
```

测试使用独立 SQLite 文件，运行后自动删除；并发测试用两个线程同时抢最后一间房，断言只有一单成功。

## 7. 设计取舍

- **SQLite 而非内存字典**：为了让事务、唯一键、条件更新和审计真正落地，而不是只在服务层“看起来正确”。
- **金额用 Decimal + TEXT**：避免浮点误差进入退款和对账。
- **服务层持有事务边界**：库存锁定、订单写入、审计写入要么同时成功，要么同时回滚。
- **两个独立程序而非一个窗口切角色**：客人端是 390×844 竖屏程序，员工端是 1360×860 桌面程序；共享数据库和服务层，但入口、窗口、导航互不混用。
- **Tkinter 而非 Web**：实验四、五要继续做静态分析和测试，桌面程序更容易在本地复现；同时不引入前端构建链。
- **无第三方运行时依赖**：降低安装成本，让助教可以直接 `python run_guest.py` / `python run.py`。

## 8. 已知限制

- 支付是本地模拟，不接真实渠道；退款记录 `submitted_at` 仅表示提交时间。
- 房号状态只覆盖“可用/已入住/维修”，未实现房态日历。
- 特殊日期使用相对日期生成，重启演示库后会随当天日期平移。
- 并发控制依赖 SQLite 的写锁；生产环境应替换为 MySQL 条件更新或行锁。
