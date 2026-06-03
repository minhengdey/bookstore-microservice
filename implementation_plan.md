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

### Phase 1 – Auth & User Services (Completed)
### Phase 2 – Catalog Service (Completed)
### Phase 3 – Inventory Service (Completed)
### Phase 4 – Order Service (Completed)
### Phase 5 – Payment & Shipping Services (Completed)
### Phase 6 – Notification Service (Completed)
### Phase 7 – Recommendation Service (Completed)

---

### Phase 8D – Recommendation MLOps (Current)

**Goal:** Transform the Recommendation Platform into a true production-grade MLOps ecosystem. Instead of generic infrastructure, this phase focuses entirely on automating the deployment, monitoring, A/B testing, and lifecycle of the BiLSTM models.

#### Proposed Changes:

##### 1. Advanced Model Registry & Deployment
- **`ModelVersion` Expansion**: Add `deployed_at` and `rollback_target`.
- **A/B Testing Router**: Implement a deterministic routing mechanism (`hash(user_id) % 100`) within the `RecommendationPipeline` to split traffic between models based on their `rollout_percentage`.
- **Rollback API**: Implement `POST /api/v1/models/rollback` to instantly downgrade a degraded model without restarting any containers.

##### 2. Inference & Online Metrics Tracking
- **`InferenceMetric`**: Track `latency_ms`, `candidate_count`, and `recommendation_count` per request to instantly spot if a new model version is too heavy.
- **`RecommendationFeedback`**: Track exact user interactions (`impression`, `clicked`, `purchased`) explicitly tied to a `recommendation_id` and `model_version_id`.
- **Metric Aggregation**: Create functions to calculate live Click-Through Rate (CTR), Conversion Rate (CVR), and Revenue Attribution per model version.

##### 3. Drift Detection & Auto-Retraining
- **`model_drift_worker`**: Implement a scheduled Django management command that compares the live interaction distribution (e.g., categories viewed) against the baseline distribution recorded during model training.
- **Event Trigger**: If drift exceeds a threshold, or if CTR drops significantly, the system will automatically publish a `model.retrain.requested` event to the `recommendation_events` RabbitMQ exchange.

## User Review Required
> [!IMPORTANT]
> **A/B Testing Hash**: Using `hash(user_id) % 100` ensures a consistent experience for logged-in users. For guest users (`anonymous_id`), we will apply the exact same hashing logic. Is this acceptable?

> [!WARNING]
> **Drift Baseline**: To compare live data against training data, the `ModelVersion` needs to store the baseline distribution (e.g., a JSON snapshot of category frequencies). I will add a `baseline_distribution` JSON field to the model.

## Verification Plan
- **A/B Testing**: Send requests with different `user_id`s and verify that they are routed to `BiLSTM v3` and `BiLSTM v4` according to an 90/10 split.
- **Feedback Loop**: Simulate a flow: `get_personal` -> log `impression` -> log `clicked` -> log `purchased`, and verify the Revenue Attribution increments correctly for that specific `model_version_id`.
- **Rollback**: Trigger the rollback API and verify traffic instantly reverts to the stable version.
