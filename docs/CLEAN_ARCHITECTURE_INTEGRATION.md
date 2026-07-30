# Clean Architecture Integration

## Tổng quan

Dự án đã được refactor theo Clean Architecture với 3 layers:

```
src/
├── domain/           # Enterprise Business Rules (innermost)
├── application/      # Application Business Rules
└── infrastructure/   # Adapters & Frameworks (outermost)
```

## Cấu trúc chi tiết

### Domain Layer (`src/domain/`)

Chứa business rules thuần túy, không phụ thuộc vào bất kỳ layer nào khác.

```
domain/
├── value_objects/
│   └── action_type.py      # ActionType enum
└── entities/
    ├── action.py           # AutoAction entity (SSOT)
    ├── tool.py             # Tool entity (SSOT)
    └── execution_result.py # ActionResult, CycleResult
```

**Key Features:**
- `serializable_fields()` - Single Source of Truth cho serialization
- Immutable value objects với `@dataclass(frozen=True)`
- Không có dependencies ngoài Python standard library

### Application Layer (`src/application/`)

Chứa use cases và business logic của ứng dụng.

```
application/
├── interfaces/             # Ports (abstractions)
│   ├── gateways.py         # IActionExecutorGateway, IInputBlockerGateway
│   ├── presenters.py       # ILogPresenter, IStatusPresenter
│   ├── repositories.py     # IToolRepository
│   └── stop_controller.py  # IStopController
├── services/
│   └── action_handlers/    # Strategy Pattern
│       ├── base.py         # IActionHandler, ActionHandlerRegistry
│       ├── keyboard_handler.py
│       ├── mouse_click_handler.py
│       ├── wait_handler.py
│       ├── image_detect_handler.py
│       └── read_passive_handler.py
├── use_cases/
│   ├── execute_action.py   # ExecuteActionUseCase
│   └── execute_tool.py     # ExecuteToolUseCase
├── engine.py               # CleanArchitectureEngine
└── engine_factory.py       # Factory for engine creation
```

**Design Patterns:**
- **Strategy Pattern**: ActionHandlerRegistry + IActionHandler
- **Use Case Pattern**: ExecuteActionUseCase, ExecuteToolUseCase
- **Dependency Inversion**: Interfaces (Ports) trong `interfaces/`

### Infrastructure Layer (`src/infrastructure/`)

Chứa adapters để kết nối với external systems.

```
infrastructure/
├── external/
│   ├── system_executor_adapter.py  # Wrap SystemExecutor
│   ├── input_blocker_adapter.py    # Wrap MouseController
│   └── stop_controller.py          # StopController implementation
├── ui/
│   ├── signal_log_presenter.py     # PyQt signal adapter
│   └── signal_status_presenter.py  # PyQt signal adapter
└── di_container.py                 # Dependency Injection Container
```

## Cách sử dụng

### 1. Sử dụng CleanArchitectureEngine

```python
from src.application.engine import CleanArchitectureEngine

# Tạo engine
engine = CleanArchitectureEngine(signals, executor, tool_manager)

# Start tool
engine.start(tool)

# Stop
engine.stop()

# Stop completely
engine.stop_completely()
```

### 2. Sử dụng Factory

```python
from src.application.engine_factory import create_engine

# Tạo clean architecture engine
engine = create_engine("clean", signals, executor, tool_manager)

# Hoặc legacy engine (returns None, cần handle riêng)
engine = create_engine("legacy", signals, executor, tool_manager)
```

### 3. Sử dụng Use Cases trực tiếp

```python
from src.infrastructure.di_container import DIContainer

# Tạo container
container = DIContainer(executor, signals)

# Lấy use case
execute_tool = container.get_execute_tool_use_case()

# Execute
execute_tool.execute(domain_tool)
```

## Dependency Flow

```
UI (main.py)
    ↓
CleanArchitectureEngine
    ↓
DIContainer
    ↓
Use Cases (ExecuteToolUseCase, ExecuteActionUseCase)
    ↓
Action Handlers (KeyboardHandler, MouseClickHandler, ...)
    ↓
Adapters (SystemExecutorAdapter, InputBlockerAdapter)
    ↓
Legacy Code (SystemExecutor, MouseController)
```

## Backward Compatibility

- Legacy `AutoBotEngine` trong `main.py` vẫn hoạt động bình thường
- `CleanArchitectureEngine` wrap legacy code, không thay đổi logic
- Có thể switch giữa 2 engines bất kỳ lúc nào

## Testing

```bash
# Run Clean Architecture tests
python -m pytest tests/test_clean_architecture.py -v
```

## Next Steps

1. **Migration**: Dần dần migrate logic từ `main.py` sang Use Cases
2. **Testing**: Thêm unit tests cho từng handler
3. **UI Integration**: Thêm option trong UI để switch engine
