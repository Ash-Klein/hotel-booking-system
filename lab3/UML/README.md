# UML 说明（实验三）

本目录保留两张类图：

| 文件 | 内容 | 用途 |
|---|---|---|
| `UML类图.puml` / `.png` | 实验二的核心交易域类图（11 个实体） | 说明“从哪张设计图实现” |
| `UML实现类图.puml` / `.png` | 实验三实现类图（领域 17 类 + 7 个服务 + 7 个仓储 + 独立客人端/桌面员工端界面组件） | 说明代码的分层、依赖与职责 |

## 与实验二类图的对应

| 实验二类 | 实现类 | 说明 |
|---|---|---|
| `Hotel` | `domain/models.py::Hotel` | 门店，增加营业状态、直营/加盟属性 |
| `RoomType` | `domain/models.py::RoomType` | 房型，增加容量、早餐、基准价 |
| `DailyInventory` | `domain/models.py::DailyInventory` | 保留 `available()` / `reserve()` / `release()` / `confirm()` 语义；仓储层用条件 UPDATE 保证原子性 |
| `DailyPrice` | `domain/models.py::DailyPrice` | 基准价 + 最终售价 |
| `RoomClosure` | `domain/models.py::RoomClosure` | 关房区间与原因 |
| `GroupLock` | `domain/models.py::GroupLock` | 协议锁房，含释放时间、状态 |
| `Guest` | `domain/models.py::Guest` | 手机号唯一，脱敏展示 |
| `Order` | `domain/models.py::Order` | 状态机、超时、版本号 |
| `OrderItem` | `domain/models.py::OrderItem` | 间数、已取消间数、整段房价、首晚房价快照 |
| `Payment` | `domain/models.py::Payment` | 线上/现付/改单补差 |
| `Refund` | `domain/models.py::Refund` | 退款审批与渠道提交时间 |
| UML note 中的支撑实体 | `Staff`、`OperationLog`、`OrderChange`、`Cancellation`、`ExceptionRecord`、`Room` | 权限、审计、改单/取消留痕、异常台账、房号 |

## 实现中新增的设计

1. **`Quote`**：报价值对象，无副作用；下单事务内会重新计算一次，防止“页面价格”与库存快照不一致。
2. **`ORDER_TRANSITIONS`**：把状态机的允许转换集中为白名单，服务层与领域对象共用。
3. **`Refund.first_night_amount`**：退款审批基数的显式快照，避免后续改价影响历史订单。
4. **`ExceptionRecord`**：异常订单不进入正常状态流转，必须由集团裁决后转已取消或正常离店。
5. **`Database.transaction()`**：所有库存变更、订单变更、审计写入在同一事务中；失败全部回滚。

## 重新渲染

```powershell
..\lab2\tools\plantuml.cmd -charset UTF-8 -tpng .\UML类图.puml
..\lab2\tools\plantuml.cmd -charset UTF-8 -tpng .\UML实现类图.puml
```

如果从仓库根目录执行，把路径改为 `lab2\tools\...` 和 `lab3\UML\...`。
