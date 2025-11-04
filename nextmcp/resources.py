"""
Resource registration and metadata utilities.

This module provides decorators and utilities for defining MCP resources
and resource templates with URI-based access.
"""

import inspect
import logging
import mimetypes
import re
from collections.abc import Callable
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class ResourceMetadata:
    """
    Metadata for a resource.

    Attributes:
        uri: Unique resource identifier (e.g., "file:///path/to/file")
        name: Human-readable name
        description: Description of the resource
        mime_type: MIME type of the resource content
        subscribable: Whether the resource supports change notifications
        max_subscribers: Maximum number of subscribers allowed
    """

    def __init__(
        self,
        uri: str,
        name: str | None = None,
        description: str | None = None,
        mime_type: str | None = None,
        subscribable: bool = False,
        max_subscribers: int = 100,
    ):
        self.uri = uri
        self.name = name or uri
        self.description = description
        self.mime_type = mime_type or self._detect_mime_type(uri)
        self.subscribable = subscribable
        self.max_subscribers = max_subscribers

    def _detect_mime_type(self, uri: str) -> str:
        """Auto-detect MIME type from URI."""
        # Try to guess from URI path
        mime_type, _ = mimetypes.guess_type(uri)
        return mime_type or "application/octet-stream"

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type,
            "subscribable": self.subscribable,
        }


class ResourceTemplate:
    """
    Metadata for a resource template with parameters.

    Attributes:
        uri_pattern: URI pattern with parameters (e.g., "file:///docs/{category}/{file}")
        description: Description of the template
        parameters: List of parameter names extracted from pattern
    """

    def __init__(self, uri_pattern: str, description: str | None = None):
        self.uri_pattern = uri_pattern
        self.description = description
        self.parameters = self._extract_parameters(uri_pattern)

    def _extract_parameters(self, pattern: str) -> list[str]:
        """Extract parameter names from URI pattern."""
        # Find all {param} placeholders
        matches = re.findall(r"\{([^}]+)\}", pattern)
        return matches

    def matches(self, uri: str) -> bool:
        """Check if a URI matches this template pattern."""
        # Convert pattern to regex
        regex_pattern = re.escape(self.uri_pattern)
        regex_pattern = regex_pattern.replace(r"\{", "{").replace(r"\}", "}")
        regex_pattern = re.sub(r"\{[^}]+\}", r"([^/]+)", regex_pattern)
        regex_pattern = f"^{regex_pattern}$"

        return re.match(regex_pattern, uri) is not None

    def extract_parameters(self, uri: str) -> dict[str, str]:
        """Extract parameter values from a URI that matches this template."""
        # Convert pattern to regex with named groups
        regex_pattern = re.escape(self.uri_pattern)
        regex_pattern = regex_pattern.replace(r"\{", "{").replace(r"\}", "}")
        for param in self.parameters:
            regex_pattern = regex_pattern.replace(f"{{{param}}}", f"(?P<{param}>[^/]+)")
        regex_pattern = f"^{regex_pattern}$"

        match = re.match(regex_pattern, uri)
        if match:
            return match.groupdict()
        return {}

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "uriTemplate": self.uri_pattern,
            "description": self.description,
            "parameters": self.parameters,
        }


def resource(
    uri: str,
    name: str | None = None,
    description: str | None = None,
    mime_type: str | None = None,
    subscribable: bool = False,
    max_subscribers: int = 100,
):
    """
    Decorator for defining a direct resource with a fixed URI.

    Args:
        uri: Unique resource identifier
        name: Human-readable name
        description: Description of the resource
        mime_type: MIME type of the content
        subscribable: Whether to support change notifications
        max_subscribers: Maximum number of subscribers

    Example:
        from nextmcp.resources import resource

        @resource("file:///logs/app.log", subscribable=True)
        def app_logs() -> str:
            return Path("/var/logs/app.log").read_text()
    """

    def decorator(fn: Callable) -> Callable:
        # Validate URI format
        try:
            parsed = urlparse(uri)
            if not parsed.scheme:
                logger.warning(
                    f"Resource URI '{uri}' has no scheme. Consider using a proper URI format."
                )
        except Exception as e:
            logger.warning(f"Invalid URI format '{uri}': {e}")

        # Store metadata on the function
        metadata = ResourceMetadata(
            uri=uri,
            name=name,
            description=description or fn.__doc__,
            mime_type=mime_type,
            subscribable=subscribable,
            max_subscribers=max_subscribers,
        )

        fn._resource_uri = uri
        fn._resource_metadata = metadata
        fn._resource_type = "direct"

        return fn

    return decorator


def resource_template(uri_pattern: str, description: str | None = None):
    """
    Decorator for defining a resource template with parameters.

    Args:
        uri_pattern: URI pattern with parameters in {braces}
        description: Description of the template

    Example:
        from nextmcp.resources import resource_template

        @resource_template("weather://forecast/{city}/{date}")
        async def weather_forecast(city: str, date: str) -> dict:
            return await fetch_weather(city, date)
    """

    def decorator(fn: Callable) -> Callable:
        # Create template metadata
        template = ResourceTemplate(uri_pattern=uri_pattern, description=description or fn.__doc__)

        # Validate that function parameters match template parameters
        sig = inspect.signature(fn)
        fn_params = set(sig.parameters.keys())
        template_params = set(template.parameters)

        if fn_params != template_params:
            logger.warning(
                f"Resource template '{uri_pattern}' parameters {template_params} "
                f"don't match function parameters {fn_params}"
            )

        # Store metadata on the function
        fn._resource_template = template
        fn._resource_type = "template"
        fn._resource_completions = getattr(fn, "_resource_completions", {})

        return fn

    return decorator


def template_completion(template_name: str, param_name: str):
    """
    Decorator to add parameter completion to a resource template.

    Args:
        template_name: Name of the template function
        param_name: Name of the parameter to provide completions for

    Example:
        @template_completion("weather_forecast", "city")
        def complete_cities(partial: str) -> list[str]:
            return ["London", "Paris", "Tokyo", "New York"]
    """

    def decorator(fn: Callable) -> Callable:
        # Store completion metadata
        fn._completion_template = template_name
        fn._completion_param = param_name

        return fn

    return decorator


def get_resource_metadata(fn: Callable) -> dict:
    """
    Extract metadata from a resource function.

    Args:
        fn: A function decorated with @resource or @resource_template

    Returns:
        Dictionary containing resource metadata
    """
    resource_type = getattr(fn, "_resource_type", "unknown")

    if resource_type == "direct":
        metadata = getattr(fn, "_resource_metadata", None)
        if metadata:
            return {
                "type": "direct",
                "uri": metadata.uri,
                "name": metadata.name,
                "description": metadata.description,
                "mimeType": metadata.mime_type,
                "subscribable": metadata.subscribable,
            }

    elif resource_type == "template":
        template = getattr(fn, "_resource_template", None)
        if template:
            return {
                "type": "template",
                "uriTemplate": template.uri_pattern,
                "description": template.description,
                "parameters": template.parameters,
            }

    return {"type": "unknown"}


def generate_resource_docs(resources: dict, templates: dict | None = None) -> str:
    """
    Generate markdown documentation for resources and templates.

    Args:
        resources: Dictionary mapping URIs to resource functions
        templates: Optional dictionary of resource templates

    Returns:
        Markdown-formatted documentation string
    """
    docs = ["# MCP Resources Documentation\n"]

    # Document direct resources
    if resources:
        docs.append("\n## Direct Resources\n")
        for uri, resource_fn in resources.items():
            metadata = get_resource_metadata(resource_fn)
            docs.append(f"\n### {metadata.get('name', uri)}\n")
            docs.append(f"**URI:** `{uri}`\n\n")
            docs.append(f"{metadata.get('description', '')}\n")
            docs.append(f"- **MIME Type:** {metadata.get('mimeType', 'unknown')}\n")
            if metadata.get("subscribable"):
                docs.append("- **Subscribable:** Yes\n")
            docs.append("\n---\n")

    # Document templates
    if templates:
        docs.append("\n## Resource Templates\n")
        for pattern, template_fn in templates.items():
            metadata = get_resource_metadata(template_fn)
            docs.append(f"\n### {pattern}\n")
            docs.append(f"{metadata.get('description', '')}\n")
            if metadata.get("parameters"):
                docs.append(f"\n**Parameters:** {', '.join(metadata['parameters'])}\n")
            docs.append("\n---\n")

    return "".join(docs)


class ResourceRegistry:
    """
    Registry for managing resources and templates.
    """

    def __init__(self):
        self._resources: dict = {}  # URI -> function
        self._templates: dict = {}  # pattern -> function
        self._completions: dict = {}  # template.param -> function
        self._subscriptions: dict = {}  # URI -> list of subscribers (FIFO)

    def register_resource(self, fn: Callable):
        """Register a direct resource."""
        uri = getattr(fn, "_resource_uri", None)
        if uri:
            self._resources[uri] = fn
            logger.debug(f"Registered resource: {uri}")

    def register_template(self, fn: Callable):
        """Register a resource template."""
        template = getattr(fn, "_resource_template", None)
        if template:
            self._templates[template.uri_pattern] = fn
            logger.debug(f"Registered resource template: {template.uri_pattern}")

    def register_completion(self, template_name: str, param_name: str, completion_fn: Callable):
        """Register a completion function for a template parameter."""
        key = f"{template_name}.{param_name}"
        self._completions[key] = completion_fn
        logger.debug(f"Registered template completion: {key}")

    def get_resource(self, uri: str) -> Callable | None:
        """Get a resource by URI."""
        return self._resources.get(uri)

    def get_template(self, pattern: str) -> Callable | None:
        """Get a template by pattern."""
        return self._templates.get(pattern)

    def find_template_for_uri(self, uri: str) -> tuple[Callable, dict] | None:
        """
        Find a template that matches the given URI and extract parameters.

        Returns:
            Tuple of (template_function, parameters) or None if no match
        """
        for _pattern, template_fn in self._templates.items():
            template = getattr(template_fn, "_resource_template", None)
            if template and template.matches(uri):
                params = template.extract_parameters(uri)
                return (template_fn, params)
        return None

    def subscribe(self, uri: str, subscriber_id: str) -> bool:
        """
        Subscribe to resource changes.

        Returns:
            True if subscription was successful
        """
        # Check if resource exists and is subscribable
        resource_fn = self.get_resource(uri)
        if not resource_fn:
            return False

        metadata = getattr(resource_fn, "_resource_metadata", None)
        if not metadata or not metadata.subscribable:
            return False

        # Check subscription limit
        if uri not in self._subscriptions:
            self._subscriptions[uri] = []

        if len(self._subscriptions[uri]) >= metadata.max_subscribers:
            logger.warning(f"Max subscribers reached for {uri}")
            # Remove oldest subscriber (FIFO) - first item in list
            oldest = self._subscriptions[uri].pop(0)
            logger.info(f"Removed oldest subscriber {oldest} from {uri}")

        # Add new subscriber (avoid duplicates)
        if subscriber_id not in self._subscriptions[uri]:
            self._subscriptions[uri].append(subscriber_id)
            logger.debug(f"Subscriber {subscriber_id} subscribed to {uri}")
        return True

    def unsubscribe(self, uri: str, subscriber_id: str) -> bool:
        """Unsubscribe from resource changes."""
        if uri in self._subscriptions:
            try:
                self._subscriptions[uri].remove(subscriber_id)
                logger.debug(f"Subscriber {subscriber_id} unsubscribed from {uri}")
                return True
            except ValueError:
                pass
        return False

    def get_subscribers(self, uri: str) -> list[str]:
        """Get all subscribers for a resource."""
        return self._subscriptions.get(uri, []).copy()

    def all_resources(self) -> dict:
        """Get all registered resources."""
        return self._resources.copy()

    def all_templates(self) -> dict:
        """Get all registered templates."""
        return self._templates.copy()
