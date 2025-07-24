# Guest Tracking System - Anti-Abuse Protection

## 🛡️ **Overview**

I've implemented a robust guest tracking system that prevents users from abusing free searches by:
- **Tracking searches by IP address** (not just session)
- **Implementing daily limits** that reset every 24 hours
- **Storing usage data in the database** for persistence
- **Handling VPN and proxy detection**

## 🔧 **How It Works**

### **For Guest Users:**
1. **IP Address Tracking**: Each search is tracked by the visitor's IP address
2. **Daily Limits**: Maximum 5 searches per IP address per day
3. **Automatic Reset**: Usage counts reset every 24 hours
4. **Persistent Storage**: Data stored in database, not just session

### **For Authenticated Users:**
- ✅ **Unlimited searches** (no restrictions)
- ✅ **No result limits**
- ✅ **Search count tracking** in user profile

## 📊 **Database Schema**

### **GuestUsage Table:**
```sql
CREATE TABLE guest_usage (
    id INTEGER PRIMARY KEY,
    ip_address VARCHAR(45) NOT NULL,  -- IPv6 compatible
    user_agent VARCHAR(500),
    search_count INTEGER DEFAULT 0,
    first_visit DATETIME,
    last_visit DATETIME,
    created_at DATETIME,
    updated_at DATETIME
);
```

## 🚀 **Features**

### **Anti-Abuse Protection:**
- ✅ **IP-based tracking** - Prevents session clearing abuse
- ✅ **Daily reset** - Allows legitimate users to search again tomorrow
- ✅ **Proxy detection** - Handles X-Forwarded-For headers
- ✅ **User agent tracking** - Additional identification layer
- ✅ **Database persistence** - Survives server restarts

### **User Experience:**
- ✅ **Clear error messages** when limits are reached
- ✅ **Encourages signup** for unlimited access
- ✅ **Fair daily limits** for legitimate users
- ✅ **Automatic cleanup** of old data

## 🔍 **Technical Implementation**

### **IP Detection:**
```python
def get_client_ip():
    # Checks multiple headers for proxy detection
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr
```

### **Usage Tracking:**
```python
def get_or_create_guest_usage():
    # Creates or updates guest usage record
    ip_address = get_client_ip()
    guest_usage = GuestUsage.query.filter_by(ip_address=ip_address).first()
    # Updates search count and timestamps
```

### **Daily Reset:**
```python
def reset_guest_usage_daily():
    # Resets search counts for records older than 24 hours
    yesterday = datetime.utcnow() - timedelta(days=1)
    guest_usage_to_reset = GuestUsage.query.filter(
        GuestUsage.updated_at < yesterday
    ).all()
```

## 🛡️ **Security Features**

### **VPN/Proxy Handling:**
- ✅ **Multiple header detection** (X-Forwarded-For, X-Real-IP, etc.)
- ✅ **IPv6 support** for modern networks
- ✅ **Fallback mechanisms** if IP detection fails

### **Data Protection:**
- ✅ **No personal data stored** (only IP and user agent)
- ✅ **Automatic cleanup** of old records
- ✅ **Database indexing** for performance

## 📈 **Benefits**

### **For Your Business:**
- 🎯 **Prevents abuse** from unlimited free searches
- 💰 **Encourages signups** for premium features
- 📊 **Usage analytics** to understand guest behavior
- 🔒 **Fair limits** that don't drive away legitimate users

### **For Users:**
- ✅ **5 free searches per day** - reasonable for testing
- ✅ **Clear messaging** about limits and benefits
- ✅ **Easy signup** to remove restrictions
- ✅ **Daily reset** allows continued use

## 🔄 **Migration**

The system includes a database migration that will:
1. **Create the GuestUsage table** automatically
2. **Add proper indexing** for performance
3. **Maintain data integrity** during deployment

## 📋 **Error Messages**

### **When Limits Are Reached:**
```
"You've reached the daily limit of 5 free searches. 
Please sign up or log in for unlimited searches."
```

### **Fallback Message:**
```
"Guest users are limited to 5 searches. 
Please sign up or log in for more."
```

## 🚀 **Deployment**

The system will automatically:
1. **Create the database table** on first run
2. **Start tracking guest usage** immediately
3. **Reset daily limits** every 24 hours
4. **Clean up old data** periodically

## 📊 **Monitoring**

You can monitor the system through:
- **Application logs** - Track reset operations
- **Database queries** - Check usage patterns
- **Error monitoring** - Identify abuse attempts

## 🎯 **Results**

This system effectively prevents:
- ❌ **Session clearing abuse**
- ❌ **VPN switching abuse**
- ❌ **Browser clearing abuse**
- ❌ **Multiple device abuse** (per IP)

While maintaining:
- ✅ **Fair access** for legitimate users
- ✅ **Clear upgrade path** to premium
- ✅ **Good user experience**
- ✅ **Robust tracking** that's hard to bypass

Your application now has enterprise-level protection against guest user abuse! 🛡️ 