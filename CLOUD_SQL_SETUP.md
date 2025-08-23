# Cloud SQL Solutions for Synoptic SaaS

## 🏆 **Recommended: Turso (SQLite Cloud)**

### **Why Turso?**
- **SQLite-based**: No schema changes needed
- **Edge replicas**: Global performance
- **Generous free tier**: 500 databases, 1GB storage
- **Simple setup**: 5-minute configuration
- **HTTP API**: Works perfectly with Vercel

### **Setup Steps**

1. **Sign up at [turso.tech](https://turso.tech)**
2. **Install Turso CLI**:
   ```bash
   # Windows (PowerShell)
   iwr -useb https://get.turso.tech/install.ps1 | iex
   ```

3. **Create database**:
   ```bash
   turso db create synoptic-saas
   turso db show synoptic-saas
   ```

4. **Get connection details**:
   ```bash
   turso db show synoptic-saas --url
   turso db tokens create synoptic-saas
   ```

5. **Connection string format**:
   ```
   libsql://[DATABASE-NAME]-[ORG].turso.io?authToken=[TOKEN]
   ```

---

## 🥈 **Alternative: PlanetScale (MySQL)**

### **Why PlanetScale?**
- **Serverless MySQL**: Branching like Git
- **Free tier**: 1 database, 1GB storage, 1 billion reads
- **No connection limits**: Perfect for serverless
- **Prisma integration**: Great tooling

### **Setup Steps**

1. **Sign up at [planetscale.com](https://planetscale.com)**
2. **Create database**: `synoptic-saas`
3. **Get connection string** from dashboard
4. **Format**: 
   ```
   mysql://[USERNAME]:[PASSWORD]@[HOST]/[DATABASE]?sslaccept=strict
   ```

---

## 🥉 **Alternative: Neon (PostgreSQL)**

### **Why Neon?**
- **Serverless PostgreSQL**: Auto-scaling
- **Free tier**: 512MB storage, 1 database
- **Branching**: Database branches for development
- **Fast cold starts**: Sub-second activation

### **Setup Steps**

1. **Sign up at [neon.tech](https://neon.tech)**
2. **Create project**: `synoptic-saas`
3. **Copy connection string** from dashboard
4. **Format**:
   ```
   postgresql://[USERNAME]:[PASSWORD]@[HOST]/[DATABASE]?sslmode=require
   ```

---

## 📊 **Comparison Table**

| Feature | Turso (SQLite) | PlanetScale (MySQL) | Neon (PostgreSQL) |
|---------|----------------|---------------------|-------------------|
| **Free Storage** | 1GB | 1GB | 512MB |
| **Free Databases** | 500 | 1 | 1 |
| **Connection Limit** | None | None | 100 |
| **Cold Start** | Instant | Fast | Sub-second |
| **Complexity** | Lowest | Medium | Medium |
| **Schema Changes** | None needed | Migrations | Migrations |

---

## 🚀 **Recommended: Turso Setup**

### **1. Update requirements.txt**
```txt
Flask==2.3.3
Flask-SQLAlchemy==3.0.5
Flask-Login==0.6.3
Flask-Migrate==4.0.5
Werkzeug==2.3.7
requests==2.31.0
google-generativeai==0.3.2
python-dotenv==1.0.0
python-docx==0.8.11
libsql-experimental==0.10.0
```

### **2. Update app.py for Turso**
```python
# Database configuration - handle multiple cloud SQL options
database_url = os.getenv('DATABASE_URL')
if not database_url:
    # Local development fallback
    database_url = 'sqlite:///synoptic.db'
elif database_url.startswith('libsql://'):
    # Turso SQLite cloud
    pass  # Use as-is
elif database_url.startswith('mysql://'):
    # PlanetScale MySQL
    pass  # Use as-is
elif database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql+psycopg2://', 1)
elif database_url.startswith('postgresql://'):
    database_url = database_url.replace('postgresql://', 'postgresql+psycopg2://', 1)
else:
    # Fallback to SQLite for production
    database_url = 'sqlite:////tmp/synoptic.db'
```

### **3. Vercel Environment Variables**
```
DATABASE_URL=libsql://synoptic-saas-[ORG].turso.io?authToken=[TOKEN]
SECRET_KEY=your-super-secret-production-key-here
FLASK_ENV=production
GOOGLE_API_KEY=your-google-gemini-api-key
```

---

## 💰 **Cost Comparison (Monthly)**

| Service | Free Tier | Paid Plans Start |
|---------|-----------|------------------|
| **Turso** | 500 DBs, 1GB each | $29/month |
| **PlanetScale** | 1 DB, 1GB | $39/month |
| **Neon** | 1 DB, 512MB | $19/month |
| **AWS RDS** | 12 months free | $15/month |

---

## ✅ **Benefits of Cloud SQL**

- **🚀 Zero maintenance**: No server management
- **📈 Auto-scaling**: Handles traffic spikes
- **🌍 Global**: Edge replicas worldwide
- **💾 Automatic backups**: Point-in-time recovery
- **🔒 Built-in security**: Encryption, access controls
- **⚡ Fast cold starts**: Perfect for serverless

**Recommendation**: Start with **Turso** for simplicity and SQLite compatibility!
