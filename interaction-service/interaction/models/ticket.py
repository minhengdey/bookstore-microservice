import uuid
from django.db import models
from .base import AuditBaseModel

class Ticket(AuditBaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer_id = models.IntegerField()
    order_id = models.IntegerField(null=True, blank=True)
    subject = models.CharField(max_length=255)
    content = models.TextField()
    status = models.CharField(
        max_length=20, 
        choices=[
            ('OPEN', 'Mở'),
            ('IN_PROGRESS', 'Đang xử lý'),
            ('RESOLVED', 'Đã giải quyết'),
            ('CLOSED', 'Đã đóng')
        ],
        default='OPEN'
    )

    class Meta:
        db_table = "tickets"
        ordering = ['-created_at']

class TicketReply(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='replies')
    sender_id = models.IntegerField()
    is_staff = models.BooleanField(default=False)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ticket_replies"
        ordering = ['created_at']
