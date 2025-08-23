# AWS RDS PostgreSQL Setup Guide for Synoptic SaaS

## 1. Create AWS RDS PostgreSQL Instance

### **Step 1: Access AWS RDS Console**
1. Go to [AWS Console](https://console.aws.amazon.com/)
2. Navigate to **RDS** service
3. Click **Create database**

### **Step 2: Database Configuration**
- **Engine**: PostgreSQL
- **Version**: PostgreSQL 15.4 (or latest)
- **Template**: Free tier (for testing) or Production (for live use)
- **DB Instance Identifier**: `synoptic-saas-db`
- **Master Username**: `postgres`
- **Master Password**: Choose a strong password (save this!)

### **Step 3: Instance Settings**
- **DB Instance Class**: 
  - Free tier: `db.t3.micro` (20GB storage, 1 vCPU, 1GB RAM)
  - Production: `db.t3.small` or higher
- **Storage**: 20GB General Purpose SSD (minimum)
- **Storage Autoscaling**: Enable (recommended)

### **Step 4: Connectivity**
- **VPC**: Default VPC
- **Public Access**: **Yes** (for Vercel access)
- **VPC Security Group**: Create new or use existing
- **Availability Zone**: No preference
- **Database Port**: `5432` (default)

### **Step 5: Additional Configuration**
- **Initial Database Name**: `synoptic`
- **Backup Retention**: 7 days (recommended)
- **Monitoring**: Enable Enhanced Monitoring
- **Auto Minor Version Upgrade**: Enable

## 2. Configure Security Group

### **Inbound Rules**
Add these rules to your RDS security group:

| Type | Protocol | Port | Source | Description |
|------|----------|------|---------|-------------|
| PostgreSQL | TCP | 5432 | 0.0.0.0/0 | Allow PostgreSQL access |

⚠️ **Security Note**: For production, restrict source to specific IP ranges or VPC CIDR blocks.

## 3. Get Connection Details

After RDS instance is created:

1. Go to **RDS > Databases**
2. Click your instance (`synoptic-saas-db`)
3. Copy the **Endpoint** from Connectivity & Security tab

**Connection String Format**:
```
postgresql://postgres:[PASSWORD]@[ENDPOINT]:5432/synoptic
```

**Example**:
```
postgresql://postgres:mypassword@synoptic-saas-db.abc123.us-east-1.rds.amazonaws.com:5432/synoptic
```

## 4. Configure Vercel Environment Variables

In your Vercel project dashboard, add:

```
DATABASE_URL=postgresql://postgres:[PASSWORD]@[ENDPOINT]:5432/synoptic
SECRET_KEY=your-super-secret-production-key-here
FLASK_ENV=production
GOOGLE_API_KEY=your-google-gemini-api-key
GITHUB_TOKEN=your-github-token-optional
```

## 5. AWS RDS Free Tier Limits

- **Instance Hours**: 750 hours per month (enough for 24/7 operation)
- **Storage**: 20GB General Purpose SSD
- **Backup Storage**: 20GB
- **Data Transfer**: 15GB outbound per month
- **Duration**: 12 months from AWS account creation

## 6. Cost Estimates

### **Free Tier (12 months)**
- **Cost**: $0 (within limits)
- **After free tier**: ~$15-25/month for db.t3.micro

### **Production (db.t3.small)**
- **Instance**: ~$25/month
- **Storage (20GB)**: ~$2.30/month
- **Backup**: ~$2.30/month (if exceeding 20GB)
- **Total**: ~$30/month

## 7. Benefits of AWS RDS

✅ **Managed Service**: Automated backups, patching, monitoring  
✅ **High Availability**: Multi-AZ deployments available  
✅ **Scalability**: Easy vertical and horizontal scaling  
✅ **Security**: VPC, encryption at rest and in transit  
✅ **Performance**: Performance Insights and monitoring  
✅ **Reliability**: 99.95% uptime SLA  
✅ **Global**: Available in all AWS regions  

## 8. Optional: SSL Connection

For enhanced security, enable SSL:

```python
# In your DATABASE_URL, add SSL parameters
DATABASE_URL=postgresql://postgres:password@endpoint:5432/synoptic?sslmode=require
```

## 9. Database Initialization

After deployment, visit your app's `/init-db` endpoint to create tables and admin user.

## 10. Monitoring and Maintenance

- **CloudWatch**: Monitor CPU, memory, connections
- **Performance Insights**: Query performance analysis
- **Automated Backups**: Point-in-time recovery
- **Maintenance Windows**: Schedule updates during low traffic

Your Synoptic SaaS is now configured for AWS RDS PostgreSQL!
