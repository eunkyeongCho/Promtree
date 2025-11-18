# GPU 정리

## 서버 환경
```
Distributor ID: Ubuntu
Description:    Ubuntu 22.04.5 LTS
Release:        22.04
Codename:       jammy
```

## Python
```
Python 3.12.6
```

## UV 설치
**MacOS, Linux, WSL**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows**
```powersehll
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```


## 환경 세팅
```
CUDA_VISIBLE_DEVICES=7 nohup ollama serve > ollama.log 2>&1 &
```