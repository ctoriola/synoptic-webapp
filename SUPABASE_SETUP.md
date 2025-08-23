# Supabase Setup Guide for Synoptic SaaS

## 1. Create Supabase Project

1. **Sign up at [supabase.com](https://supabase.com)**
2. **Create a new project**:
   - Project name: `synoptic-saas`
   - Database password: Choose a strong password (save this!)
   - Region: Choose closest to your users

## 2. Get Connection Details

After project creation, go to **Settings > Database**:

- **Connection string**: `postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres`
- **Project URL**: `https://[YOUR-PROJECT-REF].supabase.co`
- **Anon key**: Found in Settings > API

## 3. Set Up Database Tables

Supabase will automatically create your tables when you first run the Flask app, but you can also create them manually in the SQL Editor:

```sql
-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(120) UNIQUE NOT NULL,
    username VARCHAR(80) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    repo_url VARCHAR(500) NOT NULL,
    repo_owner VARCHAR(100) NOT NULL,
    repo_name VARCHAR(100) NOT NULL,
    project_proposal_json TEXT,
    user_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 4. Configure Vercel Environment Variables

In your Vercel dashboard, add these environment variables:

```
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres
SECRET_KEY=your-super-secret-production-key-here
FLASK_ENV=production
GOOGLE_API_KEY=your-google-gemini-api-key
GITHUB_TOKEN=your-github-token-optional
SUPABASE_URL=https://[YOUR-PROJECT-REF].supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
```

## 5. Supabase Free Tier Limits

- **Database**: 500MB storage
- **Bandwidth**: 5GB per month
- **API requests**: 50,000 per month
- **Authentication**: 50,000 monthly active users
- **Realtime**: 200 concurrent connections

## 6. Optional: Enable Row Level Security (RLS)

For enhanced security, you can enable RLS in Supabase:

```sql
-- Enable RLS on tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;

-- Create policies (example)
CREATE POLICY "Users can view own data" ON users
    FOR SELECT USING (auth.uid()::text = id::text);

CREATE POLICY "Users can view own projects" ON projects
    FOR SELECT USING (auth.uid()::text = user_id::text);
```

## 7. Monitoring and Logs

- **Database logs**: Available in Supabase dashboard
- **API logs**: Monitor in Supabase > Logs
- **Performance**: Check Database > Reports

## Benefits of Supabase

✅ **PostgreSQL database** with full SQL support  
✅ **Real-time subscriptions** (for future features)  
✅ **Built-in authentication** (can replace Flask-Login later)  
✅ **Auto-generated APIs** (REST and GraphQL)  
✅ **Dashboard for data management**  
✅ **Automatic backups** on paid plans  
✅ **Edge functions** for serverless compute  

Your Synoptic SaaS is now configured for Supabase deployment!
