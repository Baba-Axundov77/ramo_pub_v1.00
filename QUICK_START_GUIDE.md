# QUICK_START_GUIDE.md — Ramo Pub & TeaHouse System Test Guide

## 🚀 Hızlı Test Başlangıcı

### Adım 1: Gereksinimleri Kontrol Et
```bash
# Sanal ortam aktif mi?
venv\Scripts\activate

# Paketleri yükle (gerekirse)
pip install PyQt6 requests sqlalchemy flask pyjwt bcrypt
```

### Adım 2: Otomatik Test Script'ini Çalıştır
```bash
# Tam sistem testi (tüm adımları otomatik yapar)
python scripts\run_system_test.py
```

---

## 📋 Manuel Test Adımları

### 1️⃣ Veritabanı Bağlantısını Test Et
```bash
python -c "
from database.connection import init_database, get_db
ok, msg = init_database()
print('Database:', 'OK' if ok else f'ERROR: {msg}')
"
```

### 2️⃣ Web Sunucusunu Başlat
```bash
# Terminal 1: Web sunucusunu başlat
python web_app.py

# Beklenen çıktı:
# Starting Enterprise Restaurant Management System...
# Database initialized successfully
# Enterprise Restaurant Management System Ready!
# Access at: http://localhost:5000
```

### 3️⃣ Web API'yi Test Et
```bash
# Yeni terminal: API test
python scripts\test_jwt_auth.py

# Beklenen çıktı:
# 🔐 JWT Authentication Test Suite
# ✅ Login successful!
# ✅ API access successful with JWT!
```

### 4️⃣ Desktop Uygulamasını Başlat
```bash
# Terminal 2: Desktop uygulaması
python main_fixed.py

# Beklenen çıktı:
# Set QT_QPA_PLATFORM=windows for Windows compatibility
# ✅ Login window displayed
# ✅ Application started successfully!
```

---

## 🎯 Test Senaryoları

### ✅ Senaryo A: Sadece Web API
```bash
# 1. Web sunucusunu başlat
python web_app.py

# 2. API testlerini çalıştır
python scripts\test_jwt_auth.py
python scripts\test_dashboard_api.py
```

### ✅ Senaryo B: Desktop + Web (Tam Entegrasyon)
```bash
# Terminal 1: Web sunucusu
python web_app.py

# Terminal 2: Desktop uygulaması
python main_fixed.py

# Test akışı:
# 1. Desktop login penceresi açılır
# 2. Kullanıcı adı: admin, şifre: admin123
# 3. Desktop JWT token alır
# 4. Real-time veriler görünür
# 5. Offline/online mod test edilebilir
```

### ✅ Senaryo C: Performans Test
```bash
# Web sunucusu çalışırken
python scripts\test_desktop_integration.py

# Çıktı:
# 🚀 Desktop-Web Integration Test Suite
# ✅ JWT Authentication
# ✅ Performance Under Load
# ✅ Error Handling
```

---

## 🔧 Hata Ayıklama

### Web Sunucusu Çalışmıyor:
```bash
# PostgreSQL başlatıldı mı?
# .env dosyası doğru mu?
# 5432 port'u açık mı?

# Kontrol et:
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('DB_URL:', os.getenv('DATABASE_URL'))
print('JWT_SECRET:', os.getenv('JWT_SECRET_KEY', 'NOT_SET'))
"
```

### Desktop Uygulaması Çalışmıyor:
```bash
# PyQt6 yüklü mü?
python -c "from PyQt6.QtWidgets import QApplication; print('PyQt6 OK')"

# Windows uyumu test:
python main_fixed.py
```

### API Bağlantı Hatası:
```bash
# Web sunucusu çalışıyor mu?
curl http://localhost:5000/api/v2/system/health

# Beklenen: {"success": true, "status": "healthy"}
```

---

## 📊 Başarı Kriterleri

### ✅ Web API Testleri:
- [ ] Health check: 200 OK
- [ ] JWT login: Token alınıyor
- [ ] Dashboard API: Veri geliyor
- [ ] Cache: Performanslı çalışıyor

### ✅ Desktop Testleri:
- [ ] Login penceresi: Açılıyor
- [ ] API bağlantısı: Başarılı
- [ ] JWT authentication: Çalışıyor
- [ ] Real-time veri: Geliyor
- [ ] Offline mode: Uyarı veriyor

### ✅ Entegrasyon Testleri:
- [ ] Web ↔ Desktop: Senkronizasyon
- [ ] Token refresh: Otomatik
- [ ] Error handling: Graceful
- [ ] Performance: <200ms response

---

## 🎯 Hızlı Komutlar

```bash
# Tam test (otomatik)
python scripts\run_system_test.py

# Sadece web test
python web_app.py & python scripts\test_jwt_auth.py

# Sadece desktop test
python main_fixed.py

# Performans test
python scripts\test_desktop_integration.py

# Temizlik (process'leri durdur)
taskkill /f /im python.exe
```

---

## 🏆 Sonuç

Tüm testler başarılı olduğunda:
- ✅ Web API enterprise-level çalışıyor
- ✅ Desktop uygulaması modern UI ile çalışıyor  
- ✅ JWT güvenliği tam entegre
- ✅ Real-time veri akışı aktif
- ✅ Offline mode koruması var

**Proje production-ready!** 🚀
