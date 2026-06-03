# Final Implementation Plan – E‑Commerce Microservices (Senior Review Adjustments)

## Overview
The architecture has been refined based on a Senior/Staff Engineer review. The goal is a production‑ready, microservice‑based e‑commerce platform with clear bounded contexts, no cross‑service foreign keys, robust outbox and saga patterns, full tracing, and proper idempotency.

## Service Layout
We now expose **nine** services (instead of six) to keep responsibilities clear:

| Service | Responsibility |
|---------|-------------------|
| **auth-service** | Authentication, user accounts, refresh‑token management |
| **user-service** | User profile data (demographic info, wishlist, addresses) |
| **catalog-service** | Brands, Categories, Products, ProductVariants, Images, Reviews |
| **inventory-service** | Stock levels, reservations, optimistic locking |
| **order-service** | Cart, Order & OrderItem snapshots, promotion application, order saga |
| **payment‑service** | Payment processing, idempotency, refund lifecycle |
| **shipping-service** | Shipping tracking, carrier integration |
| **notification-service** | User notifications, metadata, read state |
| **recommendation-service** | Embedding storage (pgvector), recommendation results |

All services own their own PostgreSQL database.

## Core Model Adjustments

### Auth Service
```python
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
import uuid

class AuthUserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra):
        if not username:
            raise ValueError('The username must be set')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra):
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        return self.create_user(username, email, password, **extra)

class AuthUser(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    # Django supplies `password` (hashed) – no `password_hash` column
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    last_login_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    objects = AuthUserManager()
```

### Refresh Token Management (Auth Service)
```python
class RefreshToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('auth.AuthUser', on_delete=models.CASCADE, related_name='refresh_tokens')
    token_hash = models.CharField(max_length=255, unique=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

### User Service – UserProfile PK
```python
class UserProfile(SoftDeleteModel):
    auth_user_id = models.UUIDField(primary_key=True)  # one‑to‑one with AuthUser, no extra PK
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.CUSTOMER)
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True)
    avatar_url = models.URLField(blank=True)
    gender = models.CharField(max_length=10, blank=True)
    birthday = models.DateField(null=True, blank=True)
```

### Catalog Service – Category Model
```python
class Category(AuditBaseModel):
    name = models.CharField(max_length=255)
    parent_id = models.UUIDField(null=True, blank=True)
    slug = models.SlugField(unique=True)
    full_path = models.CharField(max_length=1024)  # e.g. "electronics/mobile/android"
    level = models.PositiveSmallIntegerField()
```

### Promotion Model & PromotionTarget (Order Service)
```python
class Promotion(models.Model):
    code = models.CharField(max_length=50, unique=True)
    # other fields omitted for brevity

class PromotionTarget(models.Model):
    promotion = models.ForeignKey('order.Promotion', on_delete=models.CASCADE, related_name='targets')
    target_type = models.CharField(max_length=20, choices=TargetType.choices)
    target_id = models.UUIDField()
```
*FK kept while promotion stays in the same service; can be swapped for a UUID later if the service splits.*

### Notification Model – Indexes
```python
class Notification(AuditBaseModel):
    user_id = models.UUIDField()
    type = models.CharField(max_length=50)
    title = models.CharField(max_length=255)
    content = models.TextField()
    action_url = models.URLField(null=True, blank=True)
    metadata = models.JSONField(default=dict)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user_id"]),
            models.Index(fields=["user_id", "read_at"]),
            models.Index(fields=["created_at"]),
        ]
```
`read_at` is the single source of truth; no separate status flag.

### Payment Model – Extended Statuses
```python
class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_id = models.UUIDField()
    gateway = models.CharField(max_length=50)
    transaction_ref = models.CharField(max_length=255, unique=True)
    idempotency_key = models.UUIDField(unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'PENDING'),
            ('PROCESSING', 'PROCESSING'),
            ('SUCCESS', 'SUCCESS'),
            ('FAILED', 'FAILED'),
            ('REFUNDED', 'REFUNDED'),
            ('PARTIALLY_REFUNDED', 'PARTIALLY_REFUNDED'),
            ('CANCELLED', 'CANCELLED'),
        ]
    )
    gateway_response = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### OutboxEvent – Published State
```python
class OutboxEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    aggregate_id = models.UUIDField()
    aggregate_type = models.CharField(max_length=100)
    event_type = models.CharField(max_length=100)
    message_id = models.UUIDField(unique=True)  # deduplication key
    payload = models.JSONField()
    status = models.CharField(
        max_length=20,
        choices=[('PENDING', 'PENDING'), ('PUBLISHED', 'PUBLISHED'), ('FAILED', 'FAILED')]
    )
    retry_count = models.PositiveIntegerField(default=0)
    last_error = models.TextField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

### Inventory – StockReservation with TTL
```python
class StockReservation(models.Model):
    reservation_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_id = models.UUIDField()
    variant_id = models.UUIDField()
    quantity = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=[('PENDING', 'PENDING'), ('CONFIRMED', 'CONFIRMED'), ('RELEASED', 'RELEASED')]
    )
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
```
A background job releases any reservation whose `expires_at` is past.

### Distributed Tracing Fields (All Services)
Every request/event payload now carries:
- `trace_id`
- `span_id`
- `parent_span_id`
These follow the OpenTelemetry W3C `traceparent` header format. Services propagate them through RabbitMQ headers and HTTP calls. Indexes on `trace_id` are added to `AuditLog`.

### AuditLog – Additional Indexes
```python
class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    aggregate_id = models.UUIDField()
    aggregate_type = models.CharField(max_length=100)
    action = models.CharField(max_length=100)
    actor_id = models.UUIDField(null=True, blank=True)
    actor_type = models.CharField(max_length=100, null=True, blank=True)
    correlation_id = models.UUIDField(null=True, blank=True)
    request_id = models.UUIDField(null=True, blank=True)
    trace_id = models.CharField(max_length=32, null=True, blank=True)
    span_id = models.CharField(max_length=16, null=True, blank=True)
    payload = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['aggregate_id']),
            models.Index(fields=['correlation_id']),
            models.Index(fields=['request_id']),
            models.Index(fields=['trace_id']),
            models.Index(fields=['created_at']),
        ]
```

### Recommendation Service – Vector Embeddings
We enforce `pgvector` in production. The fallback JSON model is kept only for local development.
```python
class ProductEmbedding(models.Model):
    product_id = models.UUIDField(primary_key=True)
    embedding = VectorField(dimensions=384)  # pgvector extension required
    created_at = models.DateTimeField(auto_now_add=True)
```

### API Gateway
An API Gateway (e.g., Kong, Traefik, or Envoy) sits in front of all services. It handles:
- JWT validation (using the `AuthUser` token)
- Rate limiting per client
- Centralised logging & request tracing headers
- CORS, routing, and unified TLS termination

## Phased Migration & Implementation Roadmap
(unchanged from previous plan, now reflecting the nine‑service layout and new model fields.)

### Phase 1 – Auth & User Services
- Implement `AuthUser` with custom manager, `RefreshToken` table.
- Implement `UserProfile` using `auth_user_id` as PK, add soft‑delete manager.
- Migrate existing user data, drop duplicate columns.
- Add API‑gateway JWT validation stub.

### Phase 2 – Catalog Service
- Add `Brand`, `Category` (with `level`), `Product`, `ProductVariant` (including `is_active`).
- Add `ProductImage`, `Review` (unique per customer‑product). 
- Add `pgvector` extension and `ProductEmbedding` model.

### Phase 3 – Inventory Service
- Implement `Inventory` with `version` optimistic lock.
- Implement `StockReservation` with `expires_at` and background release worker.

### Phase 4 – Order Service
- Implement cart, order, order item snapshots, promotion application, `OrderStatusHistory`, and saga orchestration events.

### Phase 5 – Payment & Shipping Services
- Implement extended payment statuses, `idempotency_key`, and `RefreshToken` handling.
- Implement shipping tracking, outbox events.

### Phase 6 – Notification Service
- Implement `Notification` with `read_at` and indexes.

### Phase 7 – Recommendation Service
- Deploy embedding storage with pgvector, recommendation result table, Redis cache, event consumers.

### Phase 8 – Infrastructure
- Deploy API Gateway, RabbitMQ/Kafka, Redis, PostgreSQL per service.
- Configure OpenTelemetry (Jaeger/Tempo) collection.
- Finalise outbox & saga workers, health‑checks, CI/CD pipelines.

## Verification Plan
- **Automated Tests** for each service covering the new fields, idempotency, TTL release, tracing propagation, and outbox state transitions.
- **Manual Checks** via Postman/Swagger: authentication flow with refresh tokens, profile CRUD, product hierarchy queries, inventory reservation expiry, order saga success/failure paths, payment refund flows, notification read status, recommendation vector search.
- **Observability**: Verify trace IDs appear in Jaeger, logs contain `correlation_id`, and outbox events move through PUBLISHED state.

*Please review the updated plan and confirm to start Phase 1 implementation.*
