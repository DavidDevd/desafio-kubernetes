# Kubernetes FastAPI + PostgreSQL Challenge

Kubernetes project that deploys a FastAPI application connected to PostgreSQL in a local Kind cluster.

This repository demonstrates application deployment, service discovery, persistent storage, ConfigMaps, example Secrets, probes and horizontal pod autoscaling.

## What This Project Shows

- Local Kubernetes cluster with Kind
- FastAPI container image
- PostgreSQL Deployment and Service
- PersistentVolume and PersistentVolumeClaim
- ConfigMap-based application configuration
- Example Secret manifests without real credentials
- Liveness and readiness probes
- HorizontalPodAutoscaler for the API

## Architecture

```text
Namespace desafio-api
  API Deployment
  API Service
  ConfigMap
  Example Secret
  HPA
       |
       v
Namespace desafio-db
  PostgreSQL Deployment
  PostgreSQL Service
  Example Secret
  PV/PVC
```

The API connects to PostgreSQL through the internal Kubernetes DNS name:

```text
postgres-svc.desafio-db.svc.cluster.local:5432
```

## Repository Structure

```text
api/
  Dockerfile
  main.py
  requirements.txt
api-configmap.yaml
api-deployment.yaml
api-hpa.yaml
api-secret.example.yaml
db-deployment.yaml
db-pv.yaml
db-secret.example.yaml
kind-cluster.yaml
```

## How To Run

Create the local cluster:

```bash
kind create cluster --config kind-cluster.yaml
kubectl create namespace desafio-api
kubectl create namespace desafio-db
```

Build and load the API image:

```bash
cd api
docker build -t desafio-api:v1 .
kind load docker-image desafio-api:v1 --name desafio-cluster
cd ..
```

Apply the database resources:

```bash
kubectl apply -f db-secret.example.yaml
kubectl apply -f db-pv.yaml
kubectl apply -f db-deployment.yaml
```

Apply the API resources:

```bash
kubectl apply -f api-configmap.yaml
kubectl apply -f api-secret.example.yaml
kubectl apply -f api-deployment.yaml
kubectl apply -f api-hpa.yaml
```

Expose the API locally:

```bash
kubectl port-forward svc/api-svc 8080:80 -n desafio-api
```

Test it:

```bash
curl http://localhost:8080/status
curl -X POST "http://localhost:8080/dados?info=hello"
curl http://localhost:8080/dados
```

## Useful Checks

```bash
kubectl get pods -n desafio-api
kubectl get pods -n desafio-db
kubectl get svc -n desafio-api
kubectl get svc -n desafio-db
kubectl get hpa -n desafio-api
kubectl logs -f deployment/api -n desafio-api
```

## Security Notes

- Real secret manifests are ignored by Git.
- Only `*.example.yaml` Secret manifests should be committed.
- This project is intended for local study and portfolio demonstration.

