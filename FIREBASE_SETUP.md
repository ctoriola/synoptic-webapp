# Firebase Firestore Setup Guide for Synoptic SaaS

## 🔥 **Why Firebase Firestore?**

- **NoSQL Document Database**: Perfect for flexible data structures
- **Real-time Updates**: Live data synchronization
- **Generous Free Tier**: 50K reads, 20K writes, 1GB storage daily
- **Global CDN**: Fast worldwide performance
- **Built-in Security**: Authentication and security rules
- **Serverless**: Zero maintenance required

---

## 📋 **Step-by-Step Setup**

### **1. Create Firebase Project**

1. **Go to [Firebase Console](https://console.firebase.google.com/)**
2. **Click "Create a project"**
3. **Project name**: `synoptic-saas`
4. **Enable Google Analytics**: Optional (recommended)
5. **Choose Analytics account**: Default or create new

### **2. Enable Firestore Database**

1. **In Firebase Console, go to "Firestore Database"**
2. **Click "Create database"**
3. **Security rules**: Start in **test mode** (we'll secure later)
4. **Location**: Choose closest to your users (e.g., `us-central1`)

### **3. Generate Service Account Key**

1. **Go to Project Settings** (gear icon)
2. **Click "Service accounts" tab**
3. **Click "Generate new private key"**
4. **Download the JSON file** (keep it secure!)
5. **Rename to**: `firebase-service-account.json`

### **4. Get Firebase Configuration**

In Project Settings > General tab, copy your config:

```javascript
const firebaseConfig = {
  apiKey: "your-api-key",
  authDomain: "synoptic-saas.firebaseapp.com",
  projectId: "synoptic-saas",
  storageBucket: "synoptic-saas.appspot.com",
  messagingSenderId: "123456789",
  appId: "1:123456789:web:abcdef123456"
};
```

---

## 🛠️ **Flask Integration**

### **Environment Variables**

Add to your Vercel environment variables:

```
FIREBASE_PROJECT_ID=synoptic-saas
FIREBASE_PRIVATE_KEY_ID=your-private-key-id
FIREBASE_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY\n-----END PRIVATE KEY-----
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-xxxxx@synoptic-saas.iam.gserviceaccount.com
FIREBASE_CLIENT_ID=your-client-id
FIREBASE_AUTH_URI=https://accounts.google.com/o/oauth2/auth
FIREBASE_TOKEN_URI=https://oauth2.googleapis.com/token
```

### **Data Structure**

Firestore will store data like this:

```
synoptic-saas/
├── users/
│   └── {user_id}/
│       ├── email: "user@example.com"
│       ├── username: "johndoe"
│       ├── password_hash: "hashed_password"
│       ├── is_admin: false
│       └── created_at: timestamp
└── projects/
    └── {project_id}/
        ├── title: "My Project"
        ├── repo_url: "https://github.com/user/repo"
        ├── repo_owner: "user"
        ├── repo_name: "repo"
        ├── project_proposal: {...}
        ├── user_id: "user_id_reference"
        ├── created_at: timestamp
        └── updated_at: timestamp
```

---

## 💰 **Firebase Free Tier Limits**

| Resource | Free Tier | Paid Plans Start |
|----------|-----------|------------------|
| **Reads** | 50,000/day | $0.06/100K |
| **Writes** | 20,000/day | $0.18/100K |
| **Deletes** | 20,000/day | $0.02/100K |
| **Storage** | 1GB | $0.18/GB/month |
| **Bandwidth** | 10GB/month | $0.12/GB |

**Estimate for 1000 users**: ~$5-15/month

---

## 🔒 **Security Rules**

After testing, update Firestore security rules:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users can only access their own data
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
    
    // Users can only access their own projects
    match /projects/{projectId} {
      allow read, write: if request.auth != null && 
        resource.data.user_id == request.auth.uid;
    }
  }
}
```

---

## ✅ **Benefits of Firebase**

- **🚀 Instant setup**: 15-minute configuration
- **📱 Real-time**: Live data updates
- **🌍 Global**: CDN and edge locations
- **🔐 Secure**: Built-in authentication
- **📊 Analytics**: User behavior tracking
- **💾 Offline**: Client-side caching
- **🔄 Sync**: Automatic data synchronization

---

## 🎯 **Next Steps**

1. **Create Firebase project** (5 minutes)
2. **Download service account key** (2 minutes)
3. **Update Flask app** (I'll handle this)
4. **Deploy to Vercel** (5 minutes)
5. **Test the application** (5 minutes)

**Total setup time**: ~20 minutes

Your Synoptic SaaS will be running on Firebase Firestore!
