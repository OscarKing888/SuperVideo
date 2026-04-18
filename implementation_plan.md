# SuperVideo 分步实现方案

## 总体分阶段规划

| 阶段 | 内容 | 依赖 | 预估工作量 |
|------|------|------|-----------|
| Phase 1 | 视频帧提取 | 无 | **已完成** |
| Phase 2 | 鸟类识别模块 | Phase 1 | 中 |
| Phase 3 | 客户端 GUI + 本地数据库 | Phase 1, 2 | 大 |
| Phase 4 | Go 后端中心服务器 | 无 (可并行) | 大 |
| Phase 5 | 客户端上传 + 端到端联调 | Phase 3, 4 | 中 |

---

## Phase 2: 鸟类识别模块 (`src/supervideo_bird_classifier/`)

**目标**: 从 SuperPickyOrig 中提取鸟类识别核心逻辑，形成独立的、可复用的 Python 模块。

### Step 2.1: GPU 设备检测模块
- **文件**: `src/supervideo_bird_classifier/device.py`
- **参考**: `E:\SuperPickyOrig\config.py` 中的 `get_best_device()`
- **内容**:
  - 检测 CUDA / MPS / CPU 可用性
  - 返回最优 torch.device
  - 提供设备信息查询接口（显卡名称、显存等）

### Step 2.2: YOLO 鸟类检测器
- **文件**: `src/supervideo_bird_classifier/detector.py`
- **参考**: `E:\SuperPickyOrig\birdid\bird_identifier.py` 中的 `YOLOBirdDetector`
- **内容**:
  - 定义 `Detector` 抽象接口（Protocol 或 ABC）
  - 实现 `YOLOBirdDetector`：加载 YOLO11L-seg 模型，检测图片中的鸟类区域
  - 输出：边界框、置信度、分割掩码
  - 支持 lazy loading（首次调用时加载模型）

### Step 2.3: 物种分类器
- **文件**: `src/supervideo_bird_classifier/classifier.py`
- **参考**: `E:\SuperPickyOrig\birdid\osea_classifier.py`
- **内容**:
  - 定义 `Classifier` 抽象接口
  - 实现 `OSEAClassifier`：加载 ResNet34 模型，11000 类鸟类分类
  - 输入：裁剪后的鸟类区域图片
  - 输出：Top-K 物种名称 + 置信度

### Step 2.4: 质量评分器（可选）
- **文件**: `src/supervideo_bird_classifier/scorer.py`
- **参考**: `E:\SuperPickyOrig\topiq_model.py`
- **内容**:
  - TOPIQ 美学评分
  - 锐度检测
  - 用于后续结果排序和筛选

### Step 2.5: 识别流水线
- **文件**: `src/supervideo_bird_classifier/pipeline.py`
- **内容**:
  - `ClassificationPipeline` 类：串联 检测 → 裁剪 → 分类 → 评分
  - 接收一张图片（帧），返回结构化的识别结果
  - 支持批量处理（多帧）
  - 定义结果数据类：`DetectionResult`, `ClassificationResult`, `FrameAnalysis`

### Step 2.6: 鸟类数据库
- **文件**: `src/supervideo_bird_classifier/bird_db.py`
- **参考**: `E:\SuperPickyOrig\birdid\bird_database_manager.py`
- **内容**:
  - 复用 `bird_reference.sqlite` 数据库（11K 物种信息）
  - 提供物种名称查询（中文名、英文名、学名）
  - eBird 地理过滤支持（可选）

### Step 2.7: 依赖管理和模型文件
- 更新 `pyproject.toml` 添加依赖：`torch`, `ultralytics`, `timm`, `torchvision`
- 创建 `requirements_cuda.txt` 和 `requirements_cpu.txt` 区分 GPU/CPU 环境
- 创建模型下载脚本 `scripts/download_models.py`
- 模型文件存放在 `src/supervideo_bird_classifier/models/` (gitignore)

---

## Phase 3: 客户端 GUI + 本地数据库 (`client/`)

**目标**: 实现 PyQt6 桌面客户端，整合帧提取和鸟类识别，结果存入本地 SQLite。

### Step 3.1: 本地数据库设计与实现
- **文件**: `client/database/models.py`, `client/database/repository.py`, `client/database/migrations.py`
- **参考**: ABIGit 的 Repository 模式
- **数据库表设计**:

```sql
-- 视频文件记录
CREATE TABLE videos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path   TEXT NOT NULL UNIQUE,
    file_name   TEXT NOT NULL,
    file_hash   TEXT,              -- SHA256，用于去重
    duration_ms INTEGER,
    frame_count INTEGER,
    file_size   INTEGER,
    status      TEXT DEFAULT 'pending',  -- pending/processing/completed/error
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now'))
);

-- 提取的帧
CREATE TABLE frames (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id     INTEGER NOT NULL REFERENCES videos(id),
    frame_number INTEGER NOT NULL,
    file_path    TEXT NOT NULL,
    width        INTEGER,
    height       INTEGER,
    created_at   TEXT DEFAULT (datetime('now')),
    UNIQUE(video_id, frame_number)
);

-- 鸟类检测结果
CREATE TABLE detections (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    frame_id    INTEGER NOT NULL REFERENCES frames(id),
    bbox_x      REAL,
    bbox_y      REAL,
    bbox_w      REAL,
    bbox_h      REAL,
    confidence  REAL NOT NULL,
    created_at  TEXT DEFAULT (datetime('now'))
);

-- 物种分类结果
CREATE TABLE classifications (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    detection_id    INTEGER NOT NULL REFERENCES detections(id),
    species_name    TEXT NOT NULL,
    species_name_zh TEXT,
    scientific_name TEXT,
    confidence      REAL NOT NULL,
    rank            INTEGER NOT NULL DEFAULT 1,  -- Top-K 排名
    created_at      TEXT DEFAULT (datetime('now'))
);

-- 上传队列
CREATE TABLE upload_queue (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id    INTEGER NOT NULL REFERENCES videos(id),
    status      TEXT DEFAULT 'pending',  -- pending/uploading/uploaded/error
    server_url  TEXT,
    error_msg   TEXT,
    created_at  TEXT DEFAULT (datetime('now')),
    uploaded_at TEXT
);
```

- **Repository 层**:
  - `VideoRepository`: CRUD + 状态查询
  - `FrameRepository`: 帧记录读写
  - `DetectionRepository`: 检测结果读写
  - `ClassificationRepository`: 分类结果读写
  - `UploadQueueRepository`: 上传队列管理
  - 全部基于抽象接口，方便后续替换数据库实现

### Step 3.2: 客户端应用框架
- **文件**: `client/main.py`, `client/app.py`
- **参考**: `E:\SuperPickyOrig\main.py`
- **内容**:
  - QApplication 初始化
  - 全局异常处理
  - 日志配置
  - 数据库初始化

### Step 3.3: 主窗口 UI
- **文件**: `client/ui/main_window.py`
- **参考**: `E:\SuperPickyOrig\ui\main_window.py` 的布局模式
- **布局**:
  ```
  ┌─────────────────────────────────────────────┐
  │  SuperVideo Client                     [_][x]│
  ├─────────────────────────────────────────────┤
  │  [视频目录] [浏览...]                        │
  │  ┌─ 服务器设置 ──────────────────────────┐   │
  │  │ 地址: [____________]  端口: [____]    │   │
  │  │ [测试连接]                             │   │
  │  └──────────────────────────────────────┘   │
  │  [开始处理]        [上传到中心]              │
  ├─────────────────────────────────────────────┤
  │  处理进度:  ████████████░░░░░  75%  12/16   │
  │  当前: video_003.mp4 - 检测鸟类...          │
  ├─────────────────────────────────────────────┤
  │  ┌─ 结果列表 ──────────────────────────────┐│
  │  │ 视频名        │ 状态   │ 检测数 │ 物种  ││
  │  │ video_001.mp4 │ 完成   │   3   │ 白鹭  ││
  │  │ video_002.mp4 │ 完成   │   1   │ 翠鸟  ││
  │  │ video_003.mp4 │ 处理中 │  ...  │ ...   ││
  │  └──────────────────────────────────────────┘│
  ├─────────────────────────────────────────────┤
  │  状态: 就绪 | GPU: NVIDIA RTX 3080 | DB: 本地│
  └─────────────────────────────────────────────┘
  ```

### Step 3.4: 设置对话框
- **文件**: `client/ui/settings_dialog.py`
- **内容**:
  - 中心服务器地址和端口配置
  - 帧提取参数设置（提取哪几帧、缩放选项）
  - AI 模型参数设置（置信度阈值、GPU/CPU 选择）
  - 设置持久化（JSON 或 INI 文件）

### Step 3.5: 处理进度面板
- **文件**: `client/ui/progress_panel.py`
- **参考**: SuperPickyOrig 的 WorkerSignals 模式
- **内容**:
  - 总进度条（视频级别）
  - 当前视频处理阶段指示（帧提取 → 检测 → 分类）
  - 实时日志输出区域
  - 暂停/取消按钮

### Step 3.6: 结果展示面板
- **文件**: `client/ui/results_panel.py`
- **内容**:
  - 表格显示所有处理过的视频及结果汇总
  - 点击某行展开详细信息（检测到的帧、物种、置信度）
  - 缩略图预览（检测到鸟类的帧）
  - 筛选/搜索功能

### Step 3.7: Worker 线程实现
- **文件**: `client/workers/scan_worker.py`, `client/workers/classify_worker.py`, `client/workers/upload_worker.py`
- **参考**: SuperPickyOrig 的 QThread + Signal/Slot 模式
- **内容**:
  - `ScanWorker`: 扫描目录，发现视频文件，写入数据库
  - `ClassifyWorker`: 对每个视频执行 帧提取 → 鸟类识别 流水线
    - 调用 `supervideo_frame_extractor` 提取帧
    - 调用 `supervideo_bird_classifier` 进行识别
    - 结果写入本地 SQLite
    - 通过 Signal 发送进度更新
  - `UploadWorker`: 从 upload_queue 读取待上传数据，POST 到中心服务器

---

## Phase 4: Go 后端中心服务器 (`backend/`)

**目标**: 实现中心数据库服务器，接收客户端上传的识别结果，提供汇总查询和管理界面。

### Step 4.1: 项目初始化与配置
- **文件**: `backend/main.go`, `backend/internal/config/config.go`
- **参考**: ABIGit 的 main.go 和 config 模式
- **内容**:
  - `go mod init supervideo-server`
  - 依赖：`chi/v5`, `modernc.org/sqlite`, `golang.org/x/crypto`, `google/uuid`
  - 环境变量配置：`SV_HOST`, `SV_PORT`, `SV_DB_PATH`, `SV_SESSION_HOURS`

### Step 4.2: 数据库层
- **文件**: `backend/internal/database/database.go`, `backend/internal/database/migrations.go`
- **参考**: ABIGit 的 database 包 (WAL, FK, busy_timeout)
- **数据库表**:

```sql
-- 客户端注册
CREATE TABLE clients (
    id          TEXT PRIMARY KEY,    -- UUID
    name        TEXT NOT NULL,
    machine_id  TEXT UNIQUE,         -- 机器唯一标识
    last_seen   TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

-- 用户账户
CREATE TABLE users (
    id            TEXT PRIMARY KEY,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'viewer',  -- admin/manager/viewer
    created_at    TEXT DEFAULT (datetime('now'))
);

-- 用户会话
CREATE TABLE sessions (
    token      TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users(id),
    expires_at TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

-- 视频记录（聚合自各客户端）
CREATE TABLE videos (
    id           TEXT PRIMARY KEY,
    client_id    TEXT NOT NULL REFERENCES clients(id),
    file_name    TEXT NOT NULL,
    file_hash    TEXT,
    duration_ms  INTEGER,
    frame_count  INTEGER,
    uploaded_at  TEXT DEFAULT (datetime('now')),
    UNIQUE(client_id, file_hash)
);

-- 检测结果
CREATE TABLE detections (
    id          TEXT PRIMARY KEY,
    video_id    TEXT NOT NULL REFERENCES videos(id),
    frame_number INTEGER NOT NULL,
    bbox_x      REAL,
    bbox_y      REAL,
    bbox_w      REAL,
    bbox_h      REAL,
    confidence  REAL NOT NULL
);

-- 分类结果
CREATE TABLE classifications (
    id              TEXT PRIMARY KEY,
    detection_id    TEXT NOT NULL REFERENCES detections(id),
    species_name    TEXT NOT NULL,
    species_name_zh TEXT,
    scientific_name TEXT,
    confidence      REAL NOT NULL,
    rank            INTEGER NOT NULL DEFAULT 1
);
```

### Step 4.3: Domain 接口定义
- **文件**: `backend/internal/domain/` 下按实体分文件
- **参考**: ABIGit 的 domain 包
- **接口**:
  - `ClientRepository`: 客户端注册与查询
  - `VideoRepository`: 视频记录 CRUD
  - `DetectionRepository`: 检测结果批量写入与查询
  - `ClassificationRepository`: 分类结果批量写入与查询
  - `UserRepository`: 用户管理
  - `SessionRepository`: 会话管理

### Step 4.4: Store 实现层
- **文件**: `backend/internal/store/` 下按实体分文件
- **参考**: ABIGit 的 store 包 (DBTX 接口, helpers, transactor)
- **内容**:
  - 每个 Repository 接口对应一个 Store 实现
  - `helpers.go`: 通用辅助函数（时间解析、NULL 处理）
  - `transactor.go`: 事务管理器（用于批量上传的原子性）

### Step 4.5: Service 业务逻辑层
- **文件**: `backend/internal/service/`
- **核心 Service**:
  - `UploadService`: 处理客户端上传数据
    - 验证客户端身份
    - 去重（基于 file_hash）
    - 事务性批量写入视频 + 检测 + 分类数据
  - `QueryService`: 汇总查询
    - 按物种统计
    - 按客户端统计
    - 按时间范围查询
  - `UserService`: 用户注册、登录、会话管理
    - 参考 ABIGit 的密码安全实现（bcrypt cost 12）

### Step 4.6: HTTP Handlers
- **文件**: `backend/internal/handlers/`
- **路由设计**:

```
POST   /api/v1/upload            # 客户端上传识别结果 (需认证)
GET    /api/v1/videos             # 查询视频列表
GET    /api/v1/videos/{id}        # 单个视频详情
GET    /api/v1/species            # 物种统计
GET    /api/v1/clients            # 客户端列表

POST   /api/auth/register         # 用户注册
POST   /api/auth/login            # 用户登录
GET    /api/auth/me               # 当前用户信息
POST   /api/auth/logout           # 登出

GET    /api/admin/overview         # 管理面板概览数据
GET    /api/admin/clients          # 客户端管理

GET    /                           # Web 管理界面 (SPA)
```

### Step 4.7: Middleware
- **文件**: `backend/internal/handlers/middleware.go`
- **参考**: ABIGit 的中间件链
- **内容**:
  - Logger (请求日志)
  - Recoverer (panic 恢复)
  - CORS
  - SecurityHeaders
  - SessionAuth (会话认证中间件)
  - ClientAuth (客户端 API 认证 — API Key 或 Token)

### Step 4.8: Web 管理前端（简易版）
- **文件**: `backend/web/`
- **内容**:
  - 简单的 HTML + JS 管理页面（嵌入 Go 二进制）
  - 展示：物种统计、视频列表、客户端状态
  - 可后续升级为完整 SPA

---

## Phase 5: 端到端集成

### Step 5.1: 客户端上传功能
- **文件**: `client/api/client.py`
- **内容**:
  - 封装对后端 REST API 的调用
  - 实现上传协议：
    1. 注册/认证客户端
    2. 查询服务器已有的 file_hash 列表（避免重复上传）
    3. 批量上传新的视频 + 检测 + 分类数据
    4. 更新本地 upload_queue 状态
  - 支持断点续传（按视频粒度）
  - 错误重试机制

### Step 5.2: 上传 Worker 集成
- **文件**: `client/workers/upload_worker.py`
- **内容**:
  - 在 QThread 中运行上传逻辑
  - Signal 发送上传进度
  - 处理网络异常，更新 upload_queue

### Step 5.3: 端到端测试
- 创建测试脚本验证完整流程：
  1. 客户端扫描目录 → 帧提取 → 鸟类识别 → 本地存储
  2. 客户端上传 → 后端接收 → 数据持久化
  3. Web 界面查看汇总结果

---

## 实现优先级建议

**建议先并行启动 Phase 2 和 Phase 4**：
- Phase 2（鸟类识别模块）是客户端核心能力，且有成熟参考代码可提取
- Phase 4（Go 后端）与 Python 端无代码依赖，可独立开发

**推荐执行顺序**：
1. Phase 2 (Step 2.1 → 2.5) — 建立核心 AI 管线
2. Phase 4 (Step 4.1 → 4.6) — 搭建后端骨架，可并行
3. Phase 3 (Step 3.1 → 3.7) — GUI 整合 Phase 2 成果
4. Phase 5 (Step 5.1 → 5.3) — 联调上传通路

---

## 风险与注意事项

1. **模型文件体积**：YOLO + OSEA + TOPIQ 模型文件可能超过 1GB，需 gitignore 并提供下载脚本
2. **GPU 兼容性**：需测试 CUDA 和 CPU 两种模式，确保无 GPU 环境也能运行（仅速度更慢）
3. **大视频文件处理**：帧提取可能耗时较长，需确保进度反馈和取消能力
4. **数据库并发**：SQLite 单写者限制，客户端通常单线程写入问题不大；后端如果并发高需考虑升级数据库
5. **网络上传**：大量数据上传需考虑压缩、分块、超时设置
