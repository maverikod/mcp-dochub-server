# 🚀 Kubernetes Commands Documentation

Полный набор команд для управления Kubernetes через MCP сервер `ai-admin`.

## 📋 Список команд

### 🏗️ **Управление подами (Pods)**

#### `k8s_pod_create`
Создание Kubernetes подов с монтированием проекта.

```json
{
  "command": "k8s_pod_create",
  "params": {
    "project_path": "/path/to/project",  // опционально, по умолчанию текущая директория
    "image": "mcp-dochub-server:latest",
    "port": 8060,
    "namespace": "default",
    "cpu_limit": "500m",
    "memory_limit": "512Mi"
  }
}
```

#### `k8s_pod_delete`
Удаление Kubernetes подов.

```json
{
  "command": "k8s_pod_delete", 
  "params": {
    "pod_name": "ai-admin-vast-srv",  // или автоопределение по project_path
    "namespace": "default",
    "force": false
  }
}
```

#### `k8s_pod_status`
Получение статуса подов.

```json
{
  "command": "k8s_pod_status",
  "params": {
    "pod_name": "ai-admin-vast-srv",  // опционально
    "namespace": "default",
    "all_ai_admin": false  // получить все ai-admin поды
  }
}
```

### 🚀 **Управление деплойментами (Deployments)**

#### `k8s_deployment_create`
Создание Kubernetes деплойментов с автомасштабированием.

```json
{
  "command": "k8s_deployment_create",
  "params": {
    "project_path": "/path/to/project",
    "image": "ai-admin-server:latest",
    "port": 8060,
    "namespace": "default",
    "replicas": 3,
    "cpu_limit": "500m",
    "memory_limit": "512Mi",
    "cpu_request": "100m",
    "memory_request": "128Mi"
  }
}
```

**Особенности:**
- ✅ Автоматические health checks (liveness/readiness probes)
- ✅ Управление ресурсами (CPU/Memory limits & requests)
- ✅ Автомонтирование проекта в `/app`
- ✅ Автолейблы для идентификации

### 🌐 **Управление сервисами (Services)**

#### `k8s_service_create`
Создание Kubernetes сервисов для доступа к подам.

```json
{
  "command": "k8s_service_create",
  "params": {
    "project_path": "/path/to/project",
    "service_type": "NodePort",  // ClusterIP, NodePort, LoadBalancer
    "port": 8060,
    "target_port": 8060,
    "node_port": 30080,  // только для NodePort
    "namespace": "default"
  }
}
```

**Типы сервисов:**
- `ClusterIP` - внутренний доступ в кластере
- `NodePort` - доступ через порт на нодах (30000-32767)
- `LoadBalancer` - внешний load balancer (облачный)

### 📁 **Управление namespace'ами**

#### `k8s_namespace_create`
Создание namespace'ов.

```json
{
  "command": "k8s_namespace_create",
  "params": {
    "namespace": "my-project",
    "labels": {
      "environment": "development",
      "team": "backend"
    }
  }
}
```

#### `k8s_namespace_list`
Список всех namespace'ов.

```json
{
  "command": "k8s_namespace_list"
}
```

#### `k8s_namespace_delete`
Удаление namespace'ов.

```json
{
  "command": "k8s_namespace_delete",
  "params": {
    "namespace": "my-project",
    "force": false
  }
}
```

### ⚙️ **Управление конфигурацией**

#### `k8s_configmap_create`
Создание ConfigMaps для конфигураций.

```json
{
  "command": "k8s_configmap_create",
  "params": {
    "configmap_name": "app-config",
    "data": {
      "database.host": "localhost",
      "database.port": "5432",
      "app.debug": "true"
    },
    "namespace": "default",
    "project_path": "/path/to/project"
  }
}
```

#### `k8s_secret_create`
Создание Secrets для чувствительных данных.

```json
{
  "command": "k8s_secret_create",
  "params": {
    "secret_name": "app-secrets",
    "data": {
      "database.password": "secret123",
      "api.key": "api_key_value"
    },
    "secret_type": "Opaque",  // Opaque, kubernetes.io/tls, kubernetes.io/dockerconfigjson
    "namespace": "default"
  }
}
```

### 📊 **Мониторинг и отладка**

#### `k8s_logs`
Получение логов из подов.

```json
{
  "command": "k8s_logs",
  "params": {
    "pod_name": "ai-admin-vast-srv",
    "namespace": "default",
    "container": "mcp-server",  // опционально для подов с несколькими контейнерами
    "lines": 100,
    "follow": false,
    "previous": false,  // логи предыдущего инстанса
    "since": "1h"  // за последний час
  }
}
```

#### `k8s_exec`
Выполнение команд в подах.

```json
{
  "command": "k8s_exec",
  "params": {
    "command": "ls -la /app",
    "pod_name": "ai-admin-vast-srv",
    "namespace": "default",
    "container": "mcp-server",
    "interactive": false,
    "tty": false
  }
}
```

#### `k8s_port_forward`
Проброс портов для доступа к подам.

```json
{
  "command": "k8s_port_forward",
  "params": {
    "local_port": 8080,
    "remote_port": 8060,
    "pod_name": "ai-admin-vast-srv", 
    "namespace": "default",
    "background": true
  }
}
```

### 🗑️ **Универсальное удаление ресурсов**

#### `k8s_resource_delete`
Удаление любых Kubernetes ресурсов.

```json
{
  "command": "k8s_resource_delete",
  "params": {
    "resource_type": "deployment",  // pod, deployment, service, configmap, secret, namespace, ingress, pvc
    "resource_name": "ai-admin-vast-srv",
    "namespace": "default",
    "force": false
  }
}
```

## 🎯 **Workflow Examples**

### 🚀 Полный деплой проекта

```json
// 1. Создать namespace
{
  "command": "k8s_namespace_create",
  "params": {
    "namespace": "my-app",
    "labels": {"environment": "production"}
  }
}

// 2. Создать ConfigMap с настройками
{
  "command": "k8s_configmap_create", 
  "params": {
    "configmap_name": "app-config",
    "data": {"port": "8060", "env": "prod"},
    "namespace": "my-app"
  }
}

// 3. Создать Secret с паролями
{
  "command": "k8s_secret_create",
  "params": {
    "secret_name": "app-secrets",
    "data": {"db_password": "secret123"},
    "namespace": "my-app"
  }
}

// 4. Создать Deployment
{
  "command": "k8s_deployment_create",
  "params": {
    "project_path": "/home/user/my-project",
    "replicas": 3,
    "namespace": "my-app"
  }
}

// 5. Создать Service
{
  "command": "k8s_service_create", 
  "params": {
    "service_type": "LoadBalancer",
    "namespace": "my-app"
  }
}
```

### 🔍 Мониторинг и отладка

```json
// Проверить статус подов
{
  "command": "k8s_pod_status",
  "params": {
    "namespace": "my-app",
    "all_ai_admin": true
  }
}

// Получить логи
{
  "command": "k8s_logs",
  "params": {
    "namespace": "my-app", 
    "lines": 50,
    "since": "10m"
  }
}

// Выполнить команду в поде
{
  "command": "k8s_exec",
  "params": {
    "command": "ps aux",
    "namespace": "my-app"
  }
}

// Пробросить порт для отладки
{
  "command": "k8s_port_forward",
  "params": {
    "local_port": 9090,
    "remote_port": 8060,
    "namespace": "my-app"
  }
}
```

## 🏷️ **Автоматическая маркировка**

Все ресурсы автоматически получают лейблы:
- `app: ai-admin` - идентификация приложения
- `project: {project-name}` - имя проекта из пути
- Пользовательские лейблы через параметр `labels`

## 📦 **Монтирование проектов**

Все команды автоматически:
1. Определяют имя проекта из `project_path`
2. Создают Kubernetes-совместимые имена (`ai-admin-{project-name}`)
3. Монтируют директорию проекта в контейнер (`/app`)
4. Устанавливают переменную `PROJECT_PATH=/app`

## 🛠️ **Требования**

- Установленный `kubectl`
- Доступ к Kubernetes кластеру
- PyYAML >= 6.0
- python-dateutil >= 2.8.0

## 🎮 **Быстрый старт**

```bash
# 1. Собрать образ с Kubernetes командами  
docker build -t ai-admin-server:latest .

# 2. Запустить контейнер с kubectl
docker run -d -p 8060:8060 \
  -v ~/.kube:/root/.kube:ro \
  -v $(pwd):/app \
  ai-admin-server:latest

# 3. Использовать через MCP инструменты
# Команды доступны как mcp_MCP-Proxy_dochub
```

Теперь у тебя есть **полный набор Kubernetes команд** для управления кластером через MCP сервер! 🚀 