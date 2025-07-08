README
Recycling Wallet Flask API
A minimal but scalable Flask 3.0 API for a recycling wallet simulator that rewards users for depositing recyclable materials.
Features

Stateless Flask pods ready for horizontal scaling
Firebase Google Auth with server-side ID token verification
PostgreSQL with SQLAlchemy models (User, Wallet, Transaction, Withdrawal)
Rate limiting with Redis support (5 deposits per second per wallet)
Stripe integration for withdrawals (test mode/stubbed)
Five core endpoints for wallet management

Prerequisites

Python 3.12
Docker and Docker Compose
PostgreSQL client (psql)
Firebase project with Google Auth enabled
Stripe test account (optional)

Local Development Setup

Create virtual environment:
bashpython -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

Install dependencies:
bashpip install -r requirements.txt

Configure environment:
bashcp .env.example .env
# Edit .env with your values:
# - DATABASE_URL
# - FIREBASE_PROJECT_ID
# - STRIPE_SECRET_KEY (optional)

Initialize database:
bashflask db init
flask db migrate -m "Initial migration"
flask db upgrade

Run the application:
bashflask run --port 8000


The API will be available at http://localhost:8000
Docker Compose Usage
For a complete development environment with PostgreSQL and Redis:
bashdocker compose up --build
This starts:

Flask app on port 8000
PostgreSQL on port 5432
Redis on port 6379

API Endpoints
Authentication
All endpoints except /health require Firebase ID token authentication via the Authorization: Bearer <token> header.
For development/testing, you can use the bypass header:
X-Test-User-Email: test@example.com
Endpoints

GET /wallet - Get current wallet balance
POST /deposit - Deposit recyclable materials
GET /transactions?limit=50 - Get transaction history
POST /withdraw - Withdraw money to bank account
GET /withdrawals?limit=20 - Get withdrawal history
GET /health - Health check endpoint

Firebase ID Token for Testing
To get a Firebase ID token for testing:

Visit the Firebase Auth REST API documentation
Use the signInWithPassword endpoint with your test user credentials
Extract the idToken from the response
Use it in the Authorization header: Bearer <idToken>

Alternatively, use the development bypass header for quick testing:
bashcurl -H "X-Test-User-Email: test@example.com" http://localhost:8000/wallet
Postman Testing Examples
1. Get Wallet Balance
GET http://localhost:8000/wallet
Headers:
  Authorization: Bearer <firebase_id_token>
  # OR for development:
  X-Test-User-Email: test@example.com
Expected Response:
json{
  "id": "uuid-here",
  "balance_cents": 1250,
  "balance_dollars": 12.50,
  "updated_at": "2024-01-15T10:30:00.000Z"
}
2. Create Deposit
POST http://localhost:8000/deposit
Headers:
  Authorization: Bearer <firebase_id_token>
  Content-Type: application/json
Body:
{
  "material": "plastic",
  "units": 10
}
Expected Response:
json{
  "success": true,
  "transaction": {
    "id": "uuid-here",
    "transaction_type": "deposit",
    "material": "plastic",
    "units": 10,
    "amount_cents": 50,
    "amount_dollars": 0.50,
    "created_at": "2024-01-15T10:30:00.000Z"
  },
  "new_balance_cents": 1300,
  "new_balance_dollars": 13.00
}
3. Create Withdrawal
POST http://localhost:8000/withdraw
Headers:
  Authorization: Bearer <firebase_id_token>
  Content-Type: application/json
Body:
{
  "amount_cents": 1000,
  "bank_token": "tok_test_bank_account"
}
Material Rates

Plastic: 5 cents per unit
Aluminum: 10 cents per unit

Database Operations
Check wallet balance:
sqlSELECT u.email, w.balance_cents, w.balance_cents/100.0 as balance_dollars
FROM users u
JOIN wallets w ON u.id = w.user_id;
View recent transactions:
sqlSELECT u.email, t.transaction_type, t.material, t.units, t.amount_cents, t.created_at
FROM users u
JOIN transactions t ON u.id = t.user_id
ORDER BY t.created_at DESC
LIMIT 10;
View withdrawals:
sqlSELECT u.email, w.amount_cents, w.status, w.created_at
FROM users u
JOIN withdrawals w ON u.id = w.user_id
ORDER BY w.created_at DESC;
Rate Limiting
The API implements rate limiting:

5 deposits per second per wallet (configurable)
Uses Redis for distributed rate limiting
Falls back to in-memory if Redis unavailable

Production Considerations
Database Scaling
For read-heavy workloads, consider promoting a PostgreSQL replica:

Create read replica:
bash# AWS RDS example
aws rds create-db-instance-read-replica \
  --db-instance-identifier recycling-wallet-replica \
  --source-db-instance-identifier recycling-wallet-primary

Configure read-only queries:
python# In models/__init__.py, add read replica support
SQLALCHEMY_BINDS = {
    'replica': 'postgresql://user:pass@replica-host:5432/recycling_wallet'
}

# Use bind_key for read operations
transactions = Transaction.query.options(db.load_only('id', 'amount_cents'))\
    .execution_options(bind=db.get_engine(bind='replica'))\
    .filter_by(user_id=user_id).all()


Auto-scaling with Load Balancer
For horizontal pod scaling behind an Application Load Balancer:

Kubernetes Horizontal Pod Autoscaler:
yamlapiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: recycling-wallet-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: recycling-wallet
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80

Application Load Balancer configuration:
yaml# ALB ingress for AWS
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: recycling-wallet-ingress
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/healthcheck-path: /health
spec:
  rules:
  - host: api.recyclingwallet.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: recycling-wallet-service
            port:
              number: 8000

Service configuration:
yamlapiVersion: v1
kind: Service
metadata:
  name: recycling-wallet-service
spec:
  type: NodePort
  ports:
  - port: 8000
    targetPort: 8000
    protocol: TCP
  selector:
    app: recycling-wallet


Performance Monitoring
Add these environment variables for production monitoring:
env# APM and monitoring
NEW_RELIC_LICENSE_KEY=your_license_key
SENTRY_DSN=your_sentry_dsn
LOG_LEVEL=INFO

# Database connection pooling
SQLALCHEMY_ENGINE_OPTIONS='{"pool_size": 20, "max_overflow": 30, "pool_pre_ping": true}'
Security Considerations

Environment variables: Never commit real API keys to version control
HTTPS only: Use SSL termination at the load balancer level
Rate limiting: Configure Redis with proper authentication
Database security: Use connection pooling and prepared statements (handled by SQLAlchemy)
CORS: Add Flask-CORS if serving web clients from different domains

Deployment Checklist

 Set FLASK_ENV=production
 Configure proper logging levels
 Set up database backups
 Configure Redis persistence
 Set up monitoring and alerting
 Test rate limiting with load testing
 Verify Firebase token validation in production
 Test Stripe webhook endpoints (if implemented)
 Set up SSL certificates
 Configure auto-scaling policies