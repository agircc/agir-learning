# 智能体演进系统

一个基于YAML定义的过程，通过模拟经验让智能体演进的系统。

## 概览

该系统允许用户通过LLM驱动的智能体提供的模拟经验进行演进。系统功能：

1. 从YAML文件加载过程定义
2. 在数据库中创建或查找目标用户和智能体用户
3. 根据过程图模拟智能体之间的交互
4. 为目标用户生成反思和演进洞察

## 安装

```bash
# 创建并激活虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

## 使用方法

### 运行演进过程

```bash
# 使用默认的OpenAI GPT-4模型
python run_evolution.py examples/doctor.yml

# 使用Anthropic的Claude模型
python run_evolution.py examples/doctor.yml --model anthropic

# 指定特定模型名称
python run_evolution.py examples/doctor.yml --model openai --model-name gpt-4-turbo

# 启用详细日志
python run_evolution.py examples/doctor.yml -v
```

### 环境变量

在`.env`文件中设置以下环境变量：

```
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
OPENAI_API_KEY=你的openai密钥
ANTHROPIC_API_KEY=你的anthropic密钥
```

## 过程YAML格式

过程YAML文件定义演进体验：

```yaml
process:
  name: "过程名称"
  description: "过程描述"

  target_user:
    username: "目标用户的用户名"
    first_name: "用户的名"
    last_name: "用户的姓"
    # 其他用户属性
    evolution_objective: "用户应该学习什么的描述"

  nodes:
    - id: node1
      name: "节点名称"
      role: "role_id"
      description: "节点描述"
      assigned_to: "可选的用户名"  # 如果分配给目标用户

  transitions:
    - from: node1
      to: node2
    # 更多转换

  roles:
    - id: role_id
      name: "角色名称"
      description: "角色描述"

  evolution:
    method: "演进方法名称"
    description: "演进如何工作的描述"
    knowledge_sources:
      - "来源1"
      - "来源2"
```

## 项目结构

```
项目根目录/
├── run_evolution.py        # 主入口脚本
├── requirements.txt        # 项目依赖
├── .env                    # 环境变量（需要自己创建）
├── examples/               # 示例YAML文件目录
│   └── doctor.yml          # 医生示例
└── src/                    # 源代码目录
    ├── __init__.py         # 模块初始化
    ├── cli.py              # 命令行界面
    ├── evolution.py        # 主演进引擎
    ├── db/                 # 数据库工具
    │   └── __init__.py     # 数据库初始化
    ├── llms/               # LLM提供者
    │   ├── __init__.py     # LLM模块初始化
    │   ├── base.py         # 基础LLM提供者接口
    │   ├── openai.py       # OpenAI实现
    │   └── anthropic.py    # Anthropic实现
    ├── models/             # 数据模型
    │   ├── __init__.py     # 模型初始化
    │   ├── agent.py        # 智能体模型
    │   ├── process.py      # 过程模型
    │   └── role.py         # 角色模型
    └── utils/              # 工具函数
        ├── __init__.py     # 工具初始化
        ├── database.py     # 数据库工具函数
        └── yaml_loader.py  # YAML加载工具
```

## 扩展

### 添加新的LLM提供者

1. 在`src/llms/`中创建一个新提供者
2. 实现`BaseLLMProvider`接口
3. 将提供者添加到`src/llms/__init__.py`
4. 更新`src/cli.py`中的CLI以支持新提供者

### 创建自定义过程

1. 基于示例创建新的YAML文件
2. 定义节点、转换、角色和演进方法
3. 使用CLI运行过程