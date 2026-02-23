"""
Webhook Server for Real-time Sync

Handles webhooks from Linear and Notion to trigger real-time synchronization.
"""

import os
import json
import logging
import hashlib
import hmac
from typing import Dict, Any, Optional, Callable
from pathlib import Path
from datetime import datetime

try:
    from flask import Flask, request, jsonify, Response
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    logging.warning("Flask not available - webhook server disabled")

logger = logging.getLogger(__name__)


class WebhookHandler:
    """Base class for webhook handlers."""

    def handle_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Handle incoming webhook.

        Args:
            payload: Webhook payload
            headers: Request headers

        Returns:
            Response data
        """
        raise NotImplementedError


class LinearWebhookHandler(WebhookHandler):
    """Handles webhooks from Linear."""

    def __init__(self, sync_callback: Optional[Callable] = None):
        """
        Initialize Linear webhook handler.

        Args:
            sync_callback: Function to call when sync is needed
        """
        self.sync_callback = sync_callback
        self.webhook_secret = os.getenv("LINEAR_WEBHOOK_SECRET")

    def handle_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        """Handle Linear webhook."""
        # Verify webhook signature
        if self.webhook_secret:
            signature = headers.get("Linear-Signature", "")
            if not self._verify_signature(payload, signature):
                logger.warning("Invalid Linear webhook signature")
                return {"success": False, "error": "Invalid signature"}

        # Parse webhook type
        action = payload.get("action")
        type_ = payload.get("type")
        data = payload.get("data", {})

        logger.info(f"Linear webhook: {action} {type_}")

        # Handle different event types
        if type_ == "Issue":
            return self._handle_issue_event(action, data)
        elif type_ == "Project":
            return self._handle_project_event(action, data)
        elif type_ == "Comment":
            return self._handle_comment_event(action, data)
        else:
            logger.info(f"Ignoring Linear webhook type: {type_}")
            return {"success": True, "ignored": True}

    def _handle_issue_event(self, action: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Issue events."""
        issue_id = data.get("id")
        title = data.get("title", "")
        
        if action == "update":
            # Check what changed
            updated_fields = data.get("updatedFields", {})
            logger.info(f"Issue {issue_id} updated: {list(updated_fields.keys())}")
            
            # Trigger sync if relevant fields changed
            sync_fields = ["title", "description", "state", "priority", "assigneeId"]
            if any(f in updated_fields for f in sync_fields):
                self._trigger_sync("linear", issue_id, updated_fields)
        
        elif action == "create":
            logger.info(f"Issue {issue_id} created: {title}")
            self._trigger_sync("linear", issue_id, {"created": True})
        
        elif action == "remove":
            logger.info(f"Issue {issue_id} removed")
            # Handle issue deletion if needed

        return {"success": True, "issue_id": issue_id}

    def _handle_project_event(self, action: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Project events."""
        project_id = data.get("id")
        logger.info(f"Project {project_id} {action}")
        
        if action == "update":
            self._trigger_sync("linear_project", project_id, data.get("updatedFields", {}))
        
        return {"success": True, "project_id": project_id}

    def _handle_comment_event(self, action: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Comment events."""
        comment_id = data.get("id")
        issue_id = data.get("issueId")
        
        if action == "create":
            logger.info(f"Comment {comment_id} created on issue {issue_id}")
            # Could sync comments to Notion
        
        return {"success": True, "comment_id": comment_id}

    def _verify_signature(self, payload: Dict[str, Any], signature: str) -> bool:
        """Verify Linear webhook signature."""
        if not self.webhook_secret:
            return True
        
        payload_body = json.dumps(payload, sort_keys=True).encode()
        expected = hmac.new(
            self.webhook_secret.encode(),
            payload_body,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, f"sha256={expected}")

    def _trigger_sync(self, source_type: str, entity_id: str, changes: Dict[str, Any]):
        """Trigger sync callback."""
        if self.sync_callback:
            try:
                self.sync_callback(source_type, entity_id, changes)
            except Exception as e:
                logger.error(f"Sync callback failed: {e}")


class NotionWebhookHandler(WebhookHandler):
    """Handles webhooks from Notion."""

    def __init__(self, sync_callback: Optional[Callable] = None):
        """
        Initialize Notion webhook handler.

        Args:
            sync_callback: Function to call when sync is needed
        """
        self.sync_callback = sync_callback
        self.verification_token = os.getenv("NOTION_VERIFICATION_TOKEN")

    def handle_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        """Handle Notion webhook."""
        # Notion webhooks don't have signatures in the same way
        # Verification is done via challenge-response
        
        if "challenge" in payload:
            return self._handle_challenge(payload)

        # Parse webhook
        type_ = payload.get("type")
        data = payload.get(data.get("type"), {})

        logger.info(f"Notion webhook: {type_}")

        if type_ == "page":
            return self._handle_page_event(data)
        elif type_ == "database":
            return self._handle_database_event(data)
        else:
            logger.info(f"Ignoring Notion webhook type: {type_}")
            return {"success": True, "ignored": True}

    def _handle_challenge(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Notion verification challenge."""
        challenge = payload.get("challenge", "")
        return {"challenge": challenge}

    def _handle_page_event(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Page events."""
        page_id = data.get("id")
        
        # Get the change type
        if "properties" in data:
            logger.info(f"Page {page_id} properties updated")
            self._trigger_sync("notion_page", page_id, data.get("properties", {}))
        
        return {"success": True, "page_id": page_id}

    def _handle_database_event(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Database events."""
        database_id = data.get("id")
        logger.info(f"Database {database_id} updated")
        
        return {"success": True, "database_id": database_id}

    def _trigger_sync(self, source_type: str, entity_id: str, changes: Dict[str, Any]):
        """Trigger sync callback."""
        if self.sync_callback:
            try:
                self.sync_callback(source_type, entity_id, changes)
            except Exception as e:
                logger.error(f"Sync callback failed: {e}")


class WebhookServer:
    """Flask-based webhook server."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 5000,
        sync_callback: Optional[Callable] = None,
    ):
        """
        Initialize webhook server.

        Args:
            host: Server host
            port: Server port
            sync_callback: Function to call when sync is needed
        """
        if not FLASK_AVAILABLE:
            raise RuntimeError("Flask is required for webhook server")

        self.host = host
        self.port = port
        self.app = Flask(__name__)
        
        # Initialize handlers
        self.linear_handler = LinearWebhookHandler(sync_callback)
        self.notion_handler = NotionWebhookHandler(sync_callback)
        
        # Setup routes
        self._setup_routes()
        
        # Request logging
        @self.app.before_request
        def log_request():
            logger.info(f"{request.method} {request.path} from {request.remote_addr}")

    def _setup_routes(self):
        """Setup webhook routes."""
        
        @self.app.route("/health", methods=["GET"])
        def health():
            return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

        @self.app.route("/webhooks/linear", methods=["POST"])
        def linear_webhook():
            return self._handle_webhook(self.linear_handler)

        @self.app.route("/webhooks/notion", methods=["POST"])
        def notion_webhook():
            return self._handle_webhook(self.notion_handler)

        @self.app.route("/webhooks/<provider>", methods=["POST"])
        def generic_webhook(provider):
            """Generic webhook handler for other providers."""
            handler = getattr(self, f"{provider}_handler", None)
            if handler:
                return self._handle_webhook(handler)
            return jsonify({"error": f"Unknown provider: {provider}"}), 404

    def _handle_webhook(self, handler: WebhookHandler) -> Response:
        """Process webhook with given handler."""
        try:
            payload = request.get_json()
            headers = dict(request.headers)
            
            if not payload:
                return jsonify({"error": "Invalid JSON"}), 400

            result = handler.handle_webhook(payload, headers)
            
            status = 200 if result.get("success", True) else 400
            return jsonify(result), status

        except Exception as e:
            logger.exception(f"Webhook processing failed: {e}")
            return jsonify({"error": str(e)}), 500

    def run(self, debug: bool = False):
        """
        Run the webhook server.

        Args:
            debug: Enable debug mode
        """
        logger.info(f"Starting webhook server on {self.host}:{self.port}")
        self.app.run(host=self.host, port=self.port, debug=debug)

    def run_background(self):
        """Run server in background thread."""
        import threading
        
        thread = threading.Thread(
            target=self.app.run,
            kwargs={
                "host": self.host,
                "port": self.port,
                "debug": False,
                "use_reloader": False,
            }
        )
        thread.daemon = True
        thread.start()
        logger.info(f"Webhook server started in background on {self.host}:{self.port}")


def create_webhook_server(
    host: str = "0.0.0.0",
    port: int = 5000,
    sync_callback: Optional[Callable] = None,
) -> WebhookServer:
    """Create and configure webhook server."""
    return WebhookServer(host=host, port=port, sync_callback=sync_callback)


if __name__ == "__main__":
    # Example sync callback
    def on_sync_needed(source_type: str, entity_id: str, changes: Dict[str, Any]):
        logger.info(f"Sync needed: {source_type} {entity_id} - {list(changes.keys())}")
        # Would trigger actual sync here

    # Create and run server
    server = create_webhook_server(sync_callback=on_sync_needed)
    server.run(debug=True)
