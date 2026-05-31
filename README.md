# Desafio Kubernetes — API + Banco de Dados

Projeto de desafio prático de Kubernetes, implementando uma API FastAPI conectada a um banco de dados PostgreSQL, rodando em um cluster Kind local no Windows.

---

## Sumário

- [Pré-requisitos](#pré-requisitos)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Arquitetura](#arquitetura)
- [Passo a Passo — Configuração do Cluster](#passo-a-passo--configuração-do-cluster)
- [Recursos Criados](#recursos-criados)
- [Comandos de Verificação](#comandos-de-verificação)
- [Testando a Integração](#testando-a-integração)
- [Escalonamento Automático (HPA)](#escalonamento-automático-hpa)
- [Observabilidade](#observabilidade)

---

## Pré-requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado e rodando
- [Kind](https://kind.sigs.k8s.io/docs/user/quick-start/#installation) instalado
- [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/) instalado
- PowerShell

---

## Estrutura do Projeto

```
desafio-k8s/
├── kind-cluster.yaml       # Configuração do cluster Kind
├── db-secret.yaml          # Secret com credenciais do PostgreSQL
├── db-pv.yaml              # PersistentVolume e PersistentVolumeClaim
├── db-deployment.yaml      # Deployment e Service do PostgreSQL
├── api-configmap.yaml      # ConfigMap com variáveis de conexão da API
├── api-secret.yaml         # Secret com usuário/senha para a API
├── api-deployment.yaml     # Deployment e Service da API
├── api-hpa.yaml            # HorizontalPodAutoscaler da API
└── api/
    ├── main.py             # Código da API FastAPI
    ├── requirements.txt    # Dependências Python
    └── Dockerfile          # Imagem Docker da API
```

---

## Arquitetura

```
Namespace: desafio-api                  Namespace: desafio-db
┌──────────────────────────────┐        ┌──────────────────────────────┐
│  Deployment: api             │        │  Deployment: postgres         │
│  Service: api-svc (ClusterIP)│───────▶│  Service: postgres-svc        │
│  HPA: api-hpa                │        │    (ClusterIP porta 5432)     │
│  ConfigMap: api-config       │        │  Secret: postgres-secret      │
│  Secret: api-db-secret       │        │  PVC: postgres-pvc            │
│  liveness/readinessProbe     │        │  PV: postgres-pv (1Gi)        │
└──────────────────────────────┘        └──────────────────────────────┘
```

A API se comunica com o banco via DNS interno do Kubernetes:
`postgres-svc.desafio-db.svc.cluster.local:5432`

---

## Passo a Passo — Configuração do Cluster

### 1. Criar o cluster Kind

```powershell
kind create cluster --config kind-cluster.yaml
kubectl cluster-info --context kind-desafio-cluster
```

### 2. Criar os namespaces

```powershell
kubectl create namespace desafio-api
kubectl create namespace desafio-db
```

### 3. Aplicar os recursos do banco de dados

```powershell
kubectl apply -f db-secret.yaml
kubectl apply -f db-pv.yaml
kubectl apply -f db-deployment.yaml
```

### 4. Build e carregamento da imagem da API

```powershell
# Dentro da pasta api/
docker build -t desafio-api:v1 .

# Carrega a imagem no cluster Kind (sem registry externo)
kind load docker-image desafio-api:v1 --name desafio-cluster
```

### 5. Aplicar os recursos da API

```powershell
kubectl apply -f api-configmap.yaml
kubectl apply -f api-secret.yaml
kubectl apply -f api-deployment.yaml
```

### 6. Habilitar o Metrics Server e aplicar o HPA

```powershell
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Patch necessário para o Kind (desabilita verificação TLS com kubelet)
kubectl patch deployment metrics-server -n kube-system `
  --type=json `
  -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'

kubectl apply -f api-hpa.yaml
```

---

## Recursos Criados

### Namespaces

| Namespace    | Finalidade                        |
|--------------|-----------------------------------|
| desafio-api  | Isolamento dos recursos da API    |
| desafio-db   | Isolamento dos recursos do banco  |

### Deployments

| Nome      | Namespace   | Réplicas | Imagem         |
|-----------|-------------|----------|----------------|
| api       | desafio-api | 1 (HPA)  | desafio-api:v1 |
| postgres  | desafio-db  | 1        | postgres:15    |

### Services

| Nome          | Namespace   | Tipo      | Porta |
|---------------|-------------|-----------|-------|
| api-svc       | desafio-api | ClusterIP | 80    |
| postgres-svc  | desafio-db  | ClusterIP | 5432  |

### PersistentVolume / PVC

| Recurso      | Tamanho | Modo de Acesso | Montagem no container       |
|--------------|---------|----------------|-----------------------------|
| postgres-pv  | 1Gi     | ReadWriteOnce  | `/var/lib/postgresql/data`  |
| postgres-pvc | 1Gi     | ReadWriteOnce  | vinculado ao postgres-pv    |

### ConfigMap

| Nome       | Namespace   | Variáveis                          |
|------------|-------------|------------------------------------|
| api-config | desafio-api | DB_HOST, DB_PORT, DB_NAME          |

### Secrets

| Nome             | Namespace   | Variáveis                              |
|------------------|-------------|----------------------------------------|
| postgres-secret  | desafio-db  | POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB |
| api-db-secret    | desafio-api | DB_USER, DB_PASSWORD                   |

### HPA

| Nome     | Namespace   | Min | Max | CPU alvo |
|----------|-------------|-----|-----|----------|
| api-hpa  | desafio-api | 1   | 5   | 65%      |

### Probes (Deployment da API)

| Probe          | Endpoint  | Delay inicial | Intervalo |
|----------------|-----------|---------------|-----------|
| livenessProbe  | GET /status | 15s         | 10s       |
| readinessProbe | GET /status | 10s          | 5s        |

---

## Comandos de Verificação

### Status dos pods

```powershell
kubectl get pods -n desafio-api
kubectl get pods -n desafio-db
```

### Status dos services

```powershell
kubectl get svc -n desafio-api
kubectl get svc -n desafio-db
```

### Status do PVC

```powershell
kubectl get pvc -n desafio-db
kubectl get pv
```

### Status do HPA

```powershell
kubectl get hpa -n desafio-api
```

### Visão geral de todos os recursos

```powershell
kubectl get all -n desafio-api
kubectl get all -n desafio-db
```

### Detalhes de um pod específico

```powershell
kubectl describe pod <nome-do-pod> -n desafio-api
```

---

## Testando a Integração

### 1. Expor a API via port-forward

```powershell
kubectl port-forward svc/api-svc 8080:80 -n desafio-api
```

### 2. Verificar conectividade com o banco

```powershell
curl http://localhost:8080/status
# Resposta esperada: {"status": "Conexão OK"}
```

### 3. Inserir dados no banco

```powershell
curl -X POST "http://localhost:8080/dados?info=minha-informacao"
# Resposta esperada: {"mensagem": "Inserido com sucesso"}
```

### 4. Listar dados persistidos

```powershell
curl http://localhost:8080/dados
# Resposta esperada: [{"id": 1, "info": "minha-informacao"}]
```

### 5. Acessar documentação interativa da API

Com o port-forward ativo, acesse no navegador:
```
http://localhost:8080/docs
```

---

## Escalonamento Automático (HPA)

O HPA monitora a CPU do Deployment `api` e escala entre 1 e 5 réplicas, acionando quando a utilização ultrapassar 65%.

### Verificar estado atual do HPA

```powershell
kubectl get hpa -n desafio-api
kubectl describe hpa api-hpa -n desafio-api
```

### Simular carga para acionar o HPA

```powershell
# Em um terminal, inicie o port-forward
kubectl port-forward svc/api-svc 8080:80 -n desafio-api

# Em outro terminal, gere carga com um loop
while ($true) { curl http://localhost:8080/status }
```

Acompanhe o escalonamento em tempo real:

```powershell
kubectl get hpa -n desafio-api -w
kubectl get pods -n desafio-api -w
```

---

## Observabilidade

### Logs da API

```powershell
# Logs do pod da API (substituir pelo nome real do pod)
kubectl logs -f <nome-do-pod-api> -n desafio-api

# Atalho sem precisar do nome exato
kubectl logs -f deployment/api -n desafio-api
```

### Logs do banco de dados

```powershell
kubectl logs -f deployment/postgres -n desafio-db
```

### Métricas de CPU e memória (requer Metrics Server)

```powershell
kubectl top pod -n desafio-api
kubectl top pod -n desafio-db
kubectl top nodes
```

### Eventos do cluster

```powershell
kubectl get events -n desafio-api --sort-by='.lastTimestamp'
kubectl get events -n desafio-db --sort-by='.lastTimestamp'
```

---

## Endpoints da API

| Método | Rota     | Descrição                                      |
|--------|----------|------------------------------------------------|
| GET    | /status  | Verifica conectividade com o banco             |
| POST   | /dados   | Insere um registro no banco (`?info=<texto>`)  |
| GET    | /dados   | Lista todos os registros persistidos           |
| GET    | /docs    | Documentação interativa (Swagger UI)           |