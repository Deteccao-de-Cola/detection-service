# 📚 Detection API

Detection API é uma aplicação que tem como objetivo realizar o processamento de dados de provas, utilizando técnicas de redução de dimensionalidade com PCA (*Principal Component Analysis*) e agrupamento de padrões com *K-means*. O projeto oferece uma análise e detecção de padrões em dados como detecção de anomalias ou agrupamento de comportamentos semelhantes entre candidatos.
---

## 📦 Pré-requisitos

Antes de iniciar, certifique-se de ter as seguintes ferramentas instaladas:

- [Docker e Docker Compose](https://docs.docker.com/engine/install/)

---

## 📥 Clonando o Repositório

Abra o terminal e execute:

```bash
git clone https://github.com/Deteccao-de-Cola/detection-service
```
```bash
cd detection-service
```

---

## ▶️ Executando o projeto

Depois de clonar o projeto, execute:

```bash
docker network create tcc-cola-network
```

```bash
docker compose up -d
```

---
Acesse o API via:

[0.0.0.0:8000](http://0.0.0.0:8000)