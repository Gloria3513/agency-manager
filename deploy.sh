#!/bin/bash

# 배포 스크립트

echo "🚀 Agency Manager 배포를 시작합니다..."

# 1. 깃허브에 푸시
echo "📦 깃허브에 푸시 중..."
git add .
git commit -m "Update agency manager"
git push origin main

# 2. Docker 이미지 빌드 (선택사항)
echo "🐳 Docker 이미지 빌드 중..."
docker build -t agency-manager .

# 3. Docker 컨테이너 실행 (선택사항)
echo "▶️  Docker 컨테이너 실행 중..."
docker-compose up -d

echo "✅ 배포 완료!"
echo "🌐 접속: http://localhost:8501"
