# Clean Architecture Quick Reference

## Layer Responsibilities

| Layer | Responsibility | Can Import From | Cannot Import From |
|-------|---------------|-----------------|-------------------|
| **Domain** | Business logic, entities, rules | Standard library only | Any other layer |
| **Application** | Use cases, orchestration | Domain | Infrastructure, Interfaces |
| **Infrastructure** | External services, persistence | Domain, Application (factories only) | Interfaces |
| **Interfaces** | HTTP, serialization | All layers | None (outermost layer) |

## File Organization Checklist

### Domain Layer (`app/domain/`)
- [ ] `entities.py` - Business entities (immutable dataclasses)
- [ ] `repositories.py` - Repository protocols (interfaces)
- [ ] `ports.py` - External service interfaces
- [ ] `exceptions.py` - Domain-specific exceptions
- [ ] `rules.py` - Business rules and validation functions

### Application Layer (`app/application/`)
- [ ] `services.py` - Application services (use case orchestration)
- [ ] `commands.py` - Command objects (write operations)
- [ ] `queries.py` - Query objects (read operations)
- [ ] `events.py` - Domain events (if using event-driven architecture)

### Infrastructure Layer (`app/infrastructure/`)
- [ ] `models.py` - Django ORM models
- [ ] `repositories.py` - Repository implementations
- [ ] `factories.py` - Dependency injection factories
- [ ] `serializers.py` - Model-based serializers
- [ ] `adapters/` - External service adapters
- [ ] `storage.py` - File storage implementations
- [ ] `permissions.py` - Framework-specific permissions

### Interfaces Layer (`app/interfaces/`)
- [ ] `views.py` - HTTP controllers
- [ ] `entity_serializers.py` - Domain entity serializers
- [ ] `urls.py` - URL routing
- [ ] `exception_handlers.py` - HTTP error handling

## Naming Conventions Quick Guide

### Domain
```python
# Entities
class Submission:  # PascalCase, business concept

# Repository Protocols  
class SubmissionRepository(Protocol):  # EntityName + Repository

# Ports
class TextExtractorPort(Protocol):  # ServiceName + Port

# Exceptions
class ValidationError(DomainException):  # ErrorType + Error
```

### Application
```python
# Services
class SubmissionService:  # EntityName + Service

# Commands
class CreateSubmissionCommand:  # Action + EntityName + Command

# Queries  
class GetSubmissionQuery:  # Action + EntityName + Query
```

### Infrastructure
```python
# Models
class SubmissionModel(models.Model):  # EntityName + Model

# Repository Implementations
class DjangoSubmissionRepository:  # Framework + EntityName + Repository

# Adapters
class GoogleVisionAdapter:  # ServiceProvider + ServiceName + Adapter

# Factories
class ServiceFactory:  # Purpose + Factory
```

### Interfaces
```python
# ViewSets
class SubmissionViewSet(viewsets.ViewSet):  # EntityName + ViewSet

# API Views
class CreateSubmissionAPIView(APIView):  # Action + EntityName + APIView

# Serializers
class CreateSubmissionSerializer:  # Action + EntityName + Serializer
class SubmissionResponseSerializer:  # EntityName + Response + Serializer
class DomainSubmissionSerializer:  # Domain + EntityName + Serializer
```

## Common Patterns

### 1. Repository Implementation Template
```python
class DjangoEntityRepository(EntityRepository):
    def save(self, entity: Entity) -> Entity:
        model = self._entity_to_model(entity)
        model.save()
        return self._model_to_entity(model)
    
    def get(self, id: UUID) -> Optional[Entity]:
        model = EntityModel.objects.filter(id=id).first()
        return self._model_to_entity(model) if model else None
    
    def _entity_to_model(self, entity: Entity) -> EntityModel:
        # Explicit mapping logic
        pass
    
    def _model_to_entity(self, model: EntityModel) -> Entity:
        # Explicit mapping logic  
        pass
```

### 2. Application Service Template
```python
class EntityService:
    def __init__(
        self,
        entity_repo: EntityRepository,
        external_service: ExternalServicePort
    ):
        self._entity_repo = entity_repo
        self._external_service = external_service
    
    def execute_use_case(self, command: Command) -> Entity:
        # 1. Validate command
        # 2. Load entities
        # 3. Apply business rules
        # 4. Save changes
        # 5. Return result
        pass
```

### 3. Controller Template
```python
class EntityViewSet(viewsets.ViewSet):
    def create(self, request):
        # 1. Validate input
        serializer = CreateEntitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # 2. Create command
        command = CreateEntityCommand(**serializer.validated_data)
        
        # 3. Execute use case
        factory = get_service_factory()
        service = factory.create_entity_service()
        entity = service.create_entity(command)
        
        # 4. Return response
        return Response(
            EntityResponseSerializer(entity).data,
            status=status.HTTP_201_CREATED
        )
```

### 4. Factory Template
```python
class ServiceFactory:
    def create_entity_service(self) -> EntityService:
        return EntityService(
            entity_repo=self._get_entity_repository(),
            external_service=self._get_external_service()
        )
    
    def _get_entity_repository(self) -> EntityRepository:
        if self._entity_repo is None:
            self._entity_repo = DjangoEntityRepository()
        return self._entity_repo
```

## Testing Checklist

### Domain Tests
- [ ] Test entity business rules
- [ ] Test domain exceptions
- [ ] Test validation functions
- [ ] No external dependencies
- [ ] Fast execution (< 1ms per test)

### Application Tests  
- [ ] Mock all repository dependencies
- [ ] Mock all external service ports
- [ ] Test use case orchestration
- [ ] Test error handling
- [ ] Test command validation

### Infrastructure Tests
- [ ] Test repository implementations with real database
- [ ] Test adapter implementations with external services
- [ ] Test mapping functions (entity ↔ model)
- [ ] Test error translation

### Interface Tests
- [ ] Mock application services
- [ ] Test HTTP request/response handling
- [ ] Test serialization/deserialization
- [ ] Test authentication/authorization
- [ ] Test error responses

## Common Mistakes to Avoid

### ❌ Don't Do This
```python
# Domain importing framework
from django.db import models  # ❌ In domain layer

# Application importing infrastructure
from app.infrastructure.models import User  # ❌ In application layer

# Direct model access in controllers
def create_submission(request):
    submission = SubmissionModel.objects.create(...)  # ❌ Skip service layer

# Using ModelSerializer for domain entities
class SubmissionSerializer(serializers.ModelSerializer):  # ❌ Tight coupling
    class Meta:
        model = SubmissionModel
```

### ✅ Do This Instead
```python
# Pure domain entities
@dataclass(frozen=True)
class Submission:  # ✅ Framework-independent

# Application using domain interfaces
def __init__(self, submission_repo: SubmissionRepository):  # ✅ Depend on abstraction

# Controllers delegating to services
def create_submission(request):
    service = factory.create_submission_service()
    return service.create_submission(command)  # ✅ Use service layer

# Manual serializers for domain entities
class SubmissionSerializer(serializers.Serializer):  # ✅ Explicit control
    id = serializers.UUIDField()
    title = serializers.CharField()
```

## Validation Commands

```bash
# Run import linter to check architecture
python -c "from importlinter.cli import lint_imports; lint_imports()"

# Run domain tests (should be fast)
python -m pytest app/tests/test_domain_* -v

# Run architecture boundary tests
python -m pytest app/tests/test_architecture_boundaries.py -v
```

## When to Break the Rules

Clean Architecture is a guideline, not a law. Consider pragmatic exceptions for:

1. **Small, simple applications** - May not need full separation
2. **Rapid prototyping** - Can refactor to clean architecture later
3. **Framework constraints** - Some frameworks require specific patterns
4. **Performance critical paths** - May need direct database access
5. **Legacy integration** - Gradual migration may require temporary violations

Always document architectural decisions and their rationale.