# MAP-IT Kubernetes Deployment

This directory contains Kubernetes manifests for deploying MAP-IT to a Kubernetes cluster.

## Prerequisites

- Kubernetes cluster (1.24+)
- kubectl configured
- Helm (optional, for additional services)
- NGINX Ingress Controller
- cert-manager (for TLS certificates)

## Quick Start

```bash
# Create namespace and deploy
kubectl apply -k .

# Or step by step:
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f secrets.yaml  # Update with real values first!
kubectl apply -f rbac.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f ingress.yaml
kubectl apply -f hpa.yaml
kubectl apply -f pdb.yaml
```

## Configuration

### Secrets

**IMPORTANT**: Update `secrets.yaml` with your actual credentials before deploying. In production, use external secret management:

- AWS Secrets Manager with External Secrets Operator
- HashiCorp Vault
- Azure Key Vault
- Google Cloud Secret Manager

### Environment Variables

Edit `configmap.yaml` to adjust non-sensitive configuration:

- `APP_ENV`: Environment name (production, staging)
- `LOG_LEVEL`: Logging level (INFO, DEBUG, WARNING)
- `DEFAULT_AI_PROVIDER`: Default AI provider (gemini, openai)

### Scaling

The HPA is configured to scale based on CPU and memory. Adjust in `hpa.yaml`:

- `minReplicas`: Minimum pod count
- `maxReplicas`: Maximum pod count
- `targetCPUUtilization`: CPU threshold for scaling

## Files

| File | Description |
|------|-------------|
| `namespace.yaml` | Namespace definition |
| `configmap.yaml` | Non-sensitive configuration |
| `secrets.yaml` | Sensitive credentials (template) |
| `deployment.yaml` | API, Celery Worker, Celery Beat deployments |
| `service.yaml` | ClusterIP services |
| `ingress.yaml` | Ingress with TLS configuration |
| `hpa.yaml` | Horizontal Pod Autoscalers |
| `pdb.yaml` | Pod Disruption Budgets |
| `rbac.yaml` | ServiceAccount and roles |
| `kustomization.yaml` | Kustomize configuration |

## Architecture

```
                    ┌─────────────────┐
                    │   Ingress       │
                    │   (NGINX)       │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   Service       │
                    │   (ClusterIP)   │
                    └────────┬────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
    ┌───────▼───────┐ ┌──────▼──────┐ ┌──────▼──────┐
    │   API Pod 1   │ │  API Pod 2  │ │  API Pod 3  │
    │               │ │             │ │             │
    │  - FastAPI    │ │  - FastAPI  │ │  - FastAPI  │
    │  - uvicorn    │ │  - uvicorn  │ │  - uvicorn  │
    └───────────────┘ └─────────────┘ └─────────────┘
            │
            │ (Redis Broker)
            │
    ┌───────▼───────┐     ┌───────────────┐
    │ Celery Worker │ ────│ Celery Beat   │
    │   (x2-10)     │     │   (x1)        │
    └───────────────┘     └───────────────┘
```

## Monitoring

### Health Checks

- `/api/health/live`: Liveness probe endpoint
- `/api/health/ready`: Readiness probe endpoint
- `/api/health`: Full health check with dependencies

### Prometheus Metrics

Pods are annotated for Prometheus scraping:

```yaml
prometheus.io/scrape: "true"
prometheus.io/port: "8000"
prometheus.io/path: "/metrics"
```

## Troubleshooting

### Check pod status

```bash
kubectl get pods -n mapit
kubectl describe pod <pod-name> -n mapit
kubectl logs <pod-name> -n mapit
```

### Check HPA status

```bash
kubectl get hpa -n mapit
kubectl describe hpa mapit-api-hpa -n mapit
```

### Force restart

```bash
kubectl rollout restart deployment/mapit-api -n mapit
```

## Production Checklist

- [ ] Update secrets with real credentials
- [ ] Configure external secret management
- [ ] Update ingress hostname
- [ ] Configure TLS certificate
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure alerting
- [ ] Set up log aggregation (ELK/Loki)
- [ ] Test HPA scaling
- [ ] Verify PDB behavior
- [ ] Set up backup procedures
