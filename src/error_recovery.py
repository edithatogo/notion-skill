"""
Error Recovery

Handles sync failures with retry logic, dead letter queues, and recovery mechanisms.
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import hashlib

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Type of error encountered."""
    API_RATE_LIMIT = "api_rate_limit"
    API_ERROR = "api_error"
    NETWORK_ERROR = "network_error"
    VALIDATION_ERROR = "validation_error"
    CONFLICT_ERROR = "conflict_error"
    TIMEOUT_ERROR = "timeout_error"
    UNKNOWN_ERROR = "unknown_error"


class RetryStrategy(Enum):
    """Strategy for retrying failed operations."""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    NO_RETRY = "no_retry"


@dataclass
class FailedOperation:
    """Represents a failed operation."""
    id: str
    operation_type: str  # "create_page", "update_page", "sync_track", etc.
    entity_type: str
    entity_id: str
    error_type: ErrorType
    error_message: str
    payload: Dict[str, Any]
    attempt_count: int
    max_retries: int
    first_failed_at: str
    last_failed_at: str
    next_retry_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class RecoveryResult:
    """Result of a recovery attempt."""
    operation_id: str
    success: bool
    attempts_made: int
    error_message: Optional[str] = None
    recovered_at: Optional[str] = None


class ErrorRecoveryManager:
    """Manages error recovery for sync operations."""

    def __init__(
        self,
        retry_queue_dir: Optional[str] = None,
        default_max_retries: int = 3,
        default_retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
    ):
        """
        Initialize error recovery manager.

        Args:
            retry_queue_dir: Directory to store retry queue
            default_max_retries: Default maximum retry attempts
            default_retry_strategy: Default retry strategy
        """
        self.retry_queue_dir = Path(retry_queue_dir) if retry_queue_dir else None
        self.default_max_retries = default_max_retries
        self.default_retry_strategy = default_retry_strategy

        # In-memory queues
        self.retry_queue: List[FailedOperation] = []
        self.dead_letter_queue: List[FailedOperation] = []
        self.success_history: List[RecoveryResult] = []

        # Ensure retry queue directory exists
        if self.retry_queue_dir:
            self.retry_queue_dir.mkdir(parents=True, exist_ok=True)
            self._load_queues_from_disk()

    def _generate_operation_id(self, operation_type: str, entity_id: str) -> str:
        """Generate unique operation ID."""
        content = f"{operation_type}:{entity_id}:{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def handle_error(
        self,
        operation_type: str,
        entity_type: str,
        entity_id: str,
        error: Exception,
        payload: Dict[str, Any],
        attempt_count: int = 1,
        max_retries: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FailedOperation:
        """
        Handle a failed operation.

        Args:
            operation_type: Type of operation that failed
            entity_type: Type of entity being operated on
            entity_id: ID of the entity
            error: Exception that was raised
            payload: Original operation payload
            attempt_count: Current attempt number
            max_retries: Maximum retries (uses default if not specified)
            metadata: Additional metadata

        Returns:
            FailedOperation object
        """
        max_retries = max_retries or self.default_max_retries

        # Classify error
        error_type = self._classify_error(error)

        # Create failed operation
        now = datetime.now().isoformat()
        failed_op = FailedOperation(
            id=self._generate_operation_id(operation_type, entity_id),
            operation_type=operation_type,
            entity_type=entity_type,
            entity_id=entity_id,
            error_type=error_type,
            error_message=str(error),
            payload=payload,
            attempt_count=attempt_count,
            max_retries=max_retries,
            first_failed_at=now,
            last_failed_at=now,
            next_retry_at=self._calculate_next_retry(attempt_count, error_type),
            metadata=metadata,
        )

        # Add to appropriate queue
        if attempt_count >= max_retries:
            self.dead_letter_queue.append(failed_op)
            logger.warning(f"Operation {failed_op.id} moved to dead letter queue after {attempt_count} attempts")
        else:
            self.retry_queue.append(failed_op)
            logger.info(f"Operation {failed_op.id} added to retry queue (attempt {attempt_count}/{max_retries})")

        # Persist to disk if configured
        self._save_queues_to_disk()

        return failed_op

    def _classify_error(self, error: Exception) -> ErrorType:
        """Classify an exception into an error type."""
        error_str = str(error).lower()

        if "rate limit" in error_str or "429" in error_str:
            return ErrorType.API_RATE_LIMIT
        elif "network" in error_str or "connection" in error_str or "timeout" in error_str:
            return ErrorType.NETWORK_ERROR
        elif "validation" in error_str or "invalid" in error_str:
            return ErrorType.VALIDATION_ERROR
        elif "conflict" in error_str or "409" in error_str:
            return ErrorType.CONFLICT_ERROR
        elif "timeout" in error_str:
            return ErrorType.TIMEOUT_ERROR
        elif "api" in error_str or "http" in error_str:
            return ErrorType.API_ERROR
        else:
            return ErrorType.UNKNOWN_ERROR

    def _calculate_next_retry(
        self,
        attempt_count: int,
        error_type: ErrorType,
    ) -> Optional[str]:
        """Calculate when to retry based on strategy."""
        if self.default_retry_strategy == RetryStrategy.NO_RETRY:
            return None

        # Rate limits need longer delays
        if error_type == ErrorType.API_RATE_LIMIT:
            base_delay = 60  # 1 minute
        else:
            base_delay = 5  # 5 seconds

        if self.default_retry_strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay_seconds = base_delay * (2 ** (attempt_count - 1))
        elif self.default_retry_strategy == RetryStrategy.LINEAR_BACKOFF:
            delay_seconds = base_delay * attempt_count
        elif self.default_retry_strategy == RetryStrategy.FIXED_DELAY:
            delay_seconds = base_delay
        else:
            delay_seconds = base_delay

        # Cap at 1 hour
        delay_seconds = min(delay_seconds, 3600)

        next_retry = datetime.now() + timedelta(seconds=delay_seconds)
        return next_retry.isoformat()

    def process_retry_queue(
        self,
        retry_handler: Callable[[FailedOperation], bool],
    ) -> Dict[str, int]:
        """
        Process all items in the retry queue.

        Args:
            retry_handler: Function to retry the operation. Returns True if successful.

        Returns:
            Statistics about the retry processing
        """
        stats = {
            "processed": 0,
            "succeeded": 0,
            "failed": 0,
            "moved_to_dlq": 0,
        }

        # Filter to only items ready for retry
        now = datetime.now()
        ready_for_retry = []
        still_waiting = []

        for op in self.retry_queue:
            if op.next_retry_at:
                retry_time = datetime.fromisoformat(op.next_retry_at)
                if retry_time <= now:
                    ready_for_retry.append(op)
                else:
                    still_waiting.append(op)
            else:
                ready_for_retry.append(op)

        # Process ready items
        for op in ready_for_retry:
            stats["processed"] += 1

            try:
                success = retry_handler(op)

                if success:
                    stats["succeeded"] += 1
                    self.success_history.append(RecoveryResult(
                        operation_id=op.id,
                        success=True,
                        attempts_made=op.attempt_count,
                        recovered_at=datetime.now().isoformat(),
                    ))
                    logger.info(f"Successfully recovered operation {op.id}")
                else:
                    # Retry failed
                    op.attempt_count += 1
                    op.last_failed_at = datetime.now().isoformat()

                    if op.attempt_count >= op.max_retries:
                        self.dead_letter_queue.append(op)
                        stats["moved_to_dlq"] += 1
                        logger.warning(f"Operation {op.id} moved to DLQ after {op.attempt_count} attempts")
                    else:
                        op.next_retry_at = self._calculate_next_retry(op.attempt_count, op.error_type)
                        still_waiting.append(op)
                        stats["failed"] += 1

            except Exception as e:
                logger.error(f"Retry handler exception for {op.id}: {e}")
                op.attempt_count += 1
                op.error_message = str(e)

                if op.attempt_count >= op.max_retries:
                    self.dead_letter_queue.append(op)
                    stats["moved_to_dlq"] += 1
                else:
                    op.next_retry_at = self._calculate_next_retry(op.attempt_count, op.error_type)
                    still_waiting.append(op)
                    stats["failed"] += 1

        # Update retry queue
        self.retry_queue = still_waiting
        self._save_queues_to_disk()

        return stats

    def get_dead_letter_queue_report(self) -> Dict[str, Any]:
        """Generate a report of dead letter queue items."""
        by_error_type = {}
        by_entity_type = {}

        for op in self.dead_letter_queue:
            # Group by error type
            error_key = op.error_type.value
            by_error_type[error_key] = by_error_type.get(error_key, 0) + 1

            # Group by entity type
            entity_key = op.entity_type
            by_entity_type[entity_key] = by_entity_type.get(entity_key, 0) + 1

        return {
            "total_items": len(self.dead_letter_queue),
            "by_error_type": by_error_type,
            "by_entity_type": by_entity_type,
            "items": [
                {
                    "id": op.id,
                    "operation": op.operation_type,
                    "entity": f"{op.entity_type}:{op.entity_id}",
                    "error": op.error_message,
                    "attempts": op.attempt_count,
                    "first_failed": op.first_failed_at,
                }
                for op in self.dead_letter_queue
            ],
        }

    def clear_dead_letter_queue(self) -> int:
        """Clear the dead letter queue. Returns count of cleared items."""
        count = len(self.dead_letter_queue)
        self.dead_letter_queue = []
        self._save_queues_to_disk()
        logger.info(f"Cleared {count} items from dead letter queue")
        return count

    def retry_dead_letter_item(
        self,
        operation_id: str,
        retry_handler: Callable[[FailedOperation], bool],
    ) -> RecoveryResult:
        """
        Retry a specific item from the dead letter queue.

        Args:
            operation_id: ID of the operation to retry
            retry_handler: Function to retry the operation

        Returns:
            Recovery result
        """
        # Find the operation
        op_index = next(
            (i for i, op in enumerate(self.dead_letter_queue) if op.id == operation_id),
            None
        )

        if op_index is None:
            return RecoveryResult(
                operation_id=operation_id,
                success=False,
                attempts_made=0,
                error_message="Operation not found in dead letter queue",
            )

        op = self.dead_letter_queue[op_index]
        op.attempt_count += 1

        try:
            success = retry_handler(op)

            if success:
                # Remove from DLQ
                self.dead_letter_queue.pop(op_index)
                self._save_queues_to_disk()

                return RecoveryResult(
                    operation_id=operation_id,
                    success=True,
                    attempts_made=op.attempt_count,
                    recovered_at=datetime.now().isoformat(),
                )
            else:
                return RecoveryResult(
                    operation_id=operation_id,
                    success=False,
                    attempts_made=op.attempt_count,
                    error_message="Retry handler returned failure",
                )

        except Exception as e:
            return RecoveryResult(
                operation_id=operation_id,
                success=False,
                attempts_made=op.attempt_count,
                error_message=str(e),
            )

    def _save_queues_to_disk(self):
        """Save queues to disk for persistence."""
        if not self.retry_queue_dir:
            return

        try:
            # Save retry queue
            retry_file = self.retry_queue_dir / "retry_queue.json"
            with open(retry_file, "w", encoding="utf-8") as f:
                json.dump([asdict(op) for op in self.retry_queue], f, indent=2)

            # Save dead letter queue
            dlq_file = self.retry_queue_dir / "dead_letter_queue.json"
            with open(dlq_file, "w", encoding="utf-8") as f:
                json.dump([asdict(op) for op in self.dead_letter_queue], f, indent=2)

            logger.debug("Saved queues to disk")

        except Exception as e:
            logger.error(f"Failed to save queues: {e}")

    def _load_queues_from_disk(self):
        """Load queues from disk."""
        if not self.retry_queue_dir:
            return

        try:
            # Load retry queue
            retry_file = self.retry_queue_dir / "retry_queue.json"
            if retry_file.exists():
                with open(retry_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.retry_queue = [FailedOperation(**op) for op in data]

            # Load dead letter queue
            dlq_file = self.retry_queue_dir / "dead_letter_queue.json"
            if dlq_file.exists():
                with open(dlq_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.dead_letter_queue = [FailedOperation(**op) for op in data]

            logger.debug("Loaded queues from disk")

        except Exception as e:
            logger.error(f"Failed to load queues: {e}")

    def get_recovery_stats(self) -> Dict[str, Any]:
        """Get recovery statistics."""
        return {
            "retry_queue_size": len(self.retry_queue),
            "dead_letter_queue_size": len(self.dead_letter_queue),
            "total_recoveries": len(self.success_history),
            "success_rate": (
                len(self.success_history) / (len(self.success_history) + len(self.dead_letter_queue))
                if (len(self.success_history) + len(self.dead_letter_queue)) > 0
                else 1.0
            ),
        }


def with_retry(
    max_retries: int = 3,
    retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
    error_types_to_retry: Optional[List[ErrorType]] = None,
):
    """
    Decorator for adding retry logic to functions.

    Args:
        max_retries: Maximum number of retry attempts
        retry_strategy: Strategy for retry delays
        error_types_to_retry: Which error types to retry (None = all)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            recovery_manager = kwargs.pop("recovery_manager", None)
            if not recovery_manager:
                return func(*args, **kwargs)

            last_error = None
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    error_type = recovery_manager._classify_error(e)

                    # Check if we should retry this error type
                    if error_types_to_retry and error_type not in error_types_to_retry:
                        raise

                    # Calculate delay
                    if retry_strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
                        delay = 5 * (2 ** (attempt - 1))
                    elif retry_strategy == RetryStrategy.LINEAR_BACKOFF:
                        delay = 5 * attempt
                    else:
                        delay = 5

                    delay = min(delay, 60)  # Cap at 1 minute

                    if attempt < max_retries:
                        logger.warning(f"Attempt {attempt} failed: {e}. Retrying in {delay}s...")
                        time.sleep(delay)
                    else:
                        logger.error(f"All {max_retries} attempts failed")

            # All retries exhausted
            raise last_error

        return wrapper
    return decorator
