# 🐳 TripC.AI Chatbot API - Docker Deployment Guide

Hướng dẫn triển khai TripC.AI Chatbot API sử dụng Docker và Docker Compose.

## 📋 Yêu cầu hệ thống

- **Docker**: Version 20.10+
- **Docker Compose**: Version 2.0+
- **RAM**: Tối thiểu 4GB (khuyến nghị 8GB+)
- **Disk**: Tối thiểu 10GB free space
- **OS**: Linux, macOS, hoặc Windows với WSL2

## 🚀 Triển khai nhanh

### 1. Cấu hình môi trường

```bash
# Copy file cấu hình mẫu
cp env_example.txt .env

# Chỉnh sửa file .env với thông tin thực tế
nano .env
```

**Các biến môi trường bắt buộc:**
```bash
# API Keys
OPENAI_API_KEY=your_openai_api_key_here
TRIPC_API_TOKEN=your_tripc_api_token_here

# Database (cho production)
POSTGRES_PASSWORD=your_secure_password_here
```

### 2. Triển khai Development

```bash
# Sử dụng script deploy tự động
./deploy.sh development

# Hoặc chạy thủ công
docker-compose up -d --build
```

### 3. Triển khai Production

```bash
# Sử dụng script deploy tự động
./deploy.sh production

# Hoặc chạy thủ công
docker-compose -f docker-compose.prod.yml up -d --build
```

## 🏗️ Kiến trúc Docker

### Development Environment
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   TripC API     │    │   PostgreSQL    │    │     Redis       │
│   (Port 8000)   │    │   (Port 5432)   │    │   (Port 6379)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Production Environment
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Nginx       │    │   TripC API     │    │   PostgreSQL    │    │     Redis       │
│  (Port 80/443)  │───▶│   (Port 8000)   │    │   (Port 5432)   │    │   (Port 6379)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📁 Cấu trúc file Docker

```
ChatbotTripC/
├── Dockerfile                    # Docker image cho API
├── docker-compose.yml           # Development environment
├── docker-compose.prod.yml      # Production environment
├── .dockerignore                # Files to exclude from build
├── init-db.sql                  # Database initialization
├── nginx.conf                   # Nginx configuration
├── deploy.sh                    # Deployment script
├── .env                         # Environment variables
└── src/                         # Source code
```

## 🔧 Cấu hình chi tiết

### Dockerfile
- **Base Image**: Python 3.11-slim
- **Security**: Non-root user
- **Optimization**: Multi-stage build, layer caching
- **Health Check**: API health endpoint

### Docker Compose Services

#### 1. TripC API Service
```yaml
tripc-chatbot-api:
  build: .
  ports:
    - "8000:8000"
  environment:
    - OPENAI_API_KEY=${OPENAI_API_KEY}
    - TRIPC_API_TOKEN=${TRIPC_API_TOKEN}
  depends_on:
    postgres:
      condition: service_healthy
```

#### 2. PostgreSQL với PgVector
```yaml
postgres:
  image: pgvector/pgvector:pg16
  environment:
    - POSTGRES_DB=tripc_chatbot
    - POSTGRES_USER=tripc_user
    - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
  volumes:
    - postgres_data:/var/lib/postgresql/data
    - ./init-db.sql:/docker-entrypoint-initdb.d/init-db.sql
```

#### 3. Redis Cache
```yaml
redis:
  image: redis:7-alpine
  command: redis-server --appendonly yes --maxmemory 256mb
  volumes:
    - redis_data:/data
```

#### 4. Nginx (Production)
```yaml
nginx:
  image: nginx:alpine
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./nginx.conf:/etc/nginx/nginx.conf:ro
    - ./ssl:/etc/nginx/ssl:ro
```

## 🛠️ Lệnh quản lý

### Development
```bash
# Khởi động services
docker-compose up -d

# Xem logs
docker-compose logs -f

# Dừng services
docker-compose down

# Rebuild và restart
docker-compose up -d --build

# Xem status
docker-compose ps
```

### Production
```bash
# Khởi động services
docker-compose -f docker-compose.prod.yml up -d

# Xem logs
docker-compose -f docker-compose.prod.yml logs -f

# Dừng services
docker-compose -f docker-compose.prod.yml down

# Rebuild và restart
docker-compose -f docker-compose.prod.yml up -d --build
```

## 🔍 Monitoring và Debugging

### Health Checks
```bash
# API Health
curl http://localhost:8000/health

# PostgreSQL Health
docker exec tripc-postgres pg_isready -U tripc_user

# Redis Health
docker exec tripc-redis redis-cli ping
```

### Logs
```bash
# API logs
docker-compose logs tripc-chatbot-api

# Database logs
docker-compose logs postgres

# All services logs
docker-compose logs -f
```

### Database Access
```bash
# Connect to PostgreSQL
docker exec -it tripc-postgres psql -U tripc_user -d tripc_chatbot

# Backup database
docker exec tripc-postgres pg_dump -U tripc_user tripc_chatbot > backup.sql

# Restore database
docker exec -i tripc-postgres psql -U tripc_user -d tripc_chatbot < backup.sql
```

## 🔒 Bảo mật Production

### 1. SSL/TLS Configuration
```bash
# Tạo SSL certificates
mkdir -p ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/key.pem -out ssl/cert.pem
```

### 2. Environment Variables
```bash
# Sử dụng file .env riêng cho production
cp env_example.txt .env.production
# Chỉnh sửa với thông tin production
```

### 3. Firewall
```bash
# Chỉ mở ports cần thiết
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

## 📊 Performance Tuning

### Resource Limits
```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
    reservations:
      cpus: '1.0'
      memory: 1G
```

### Database Optimization
```sql
-- Tăng shared_buffers
ALTER SYSTEM SET shared_buffers = '256MB';

-- Tăng work_mem
ALTER SYSTEM SET work_mem = '4MB';

-- Reload configuration
SELECT pg_reload_conf();
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Port Already in Use
```bash
# Kiểm tra ports đang sử dụng
netstat -tulpn | grep :8000

# Kill process
sudo kill -9 <PID>
```

#### 2. Database Connection Failed
```bash
# Kiểm tra PostgreSQL logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres
```

#### 3. Memory Issues
```bash
# Kiểm tra memory usage
docker stats

# Clean up unused resources
docker system prune -a
```

#### 4. SSL Certificate Issues
```bash
# Kiểm tra certificate
openssl x509 -in ssl/cert.pem -text -noout

# Regenerate certificate
rm ssl/cert.pem ssl/key.pem
# Tạo lại như hướng dẫn ở trên
```

## 📈 Scaling

### Horizontal Scaling
```yaml
# Thêm multiple API instances
tripc-chatbot-api:
  deploy:
    replicas: 3
  environment:
    - REDIS_URL=redis://redis:6379
```

### Load Balancer
```nginx
upstream tripc_api {
    server tripc-chatbot-api-1:8000;
    server tripc-chatbot-api-2:8000;
    server tripc-chatbot-api-3:8000;
}
```

## 🔄 Backup và Recovery

### Automated Backup
```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
docker exec tripc-postgres pg_dump -U tripc_user tripc_chatbot > backups/backup_$DATE.sql
```

### Recovery
```bash
# Restore từ backup
docker exec -i tripc-postgres psql -U tripc_user -d tripc_chatbot < backups/backup_20231201_120000.sql
```

## 📞 Support

Nếu gặp vấn đề, vui lòng:

1. Kiểm tra logs: `docker-compose logs -f`
2. Kiểm tra health status: `curl http://localhost:8000/health`
3. Xem documentation: `http://localhost:8000/docs`
4. Liên hệ team: dev@tripc.ai

---

**Happy Deploying! 🚀**
