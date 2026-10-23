"""
Compatibility layer that uses native FastAPI & Pydantic v2 when installed
(e.g. in VS Code / Google Antigravity via `pip install -r requirements.txt`),
and provides a lightweight standard-library fallback for bare Python environments
so the entire test suite and ASGI router can run anywhere.
"""
from __future__ import annotations

import asyncio
import copy
import inspect
import json
import re
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, get_origin, get_args

try:
    from pydantic import BaseModel, Field, ValidationError  # type: ignore
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False

    class ValidationError(ValueError):
        """Raised when schema validation fails."""
        pass

    class _FieldInfo:
        def __init__(
            self,
            default: Any = ...,
            *,
            default_factory: Optional[Callable[[], Any]] = None,
            ge: Optional[float] = None,
            le: Optional[float] = None,
            min_length: Optional[int] = None,
            max_length: Optional[int] = None,
            description: Optional[str] = None,
        ) -> None:
            self.default = default
            self.default_factory = default_factory
            self.ge = ge
            self.le = le
            self.min_length = min_length
            self.max_length = max_length
            self.description = description

    def Field(  # type: ignore
        default: Any = ...,
        *,
        default_factory: Optional[Callable[[], Any]] = None,
        ge: Optional[float] = None,
        le: Optional[float] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        description: Optional[str] = None,
    ) -> Any:
        return _FieldInfo(
            default,
            default_factory=default_factory,
            ge=ge,
            le=le,
            min_length=min_length,
            max_length=max_length,
            description=description,
        )

    class BaseModel:  # type: ignore
        """Lightweight Pydantic v2-compatible BaseModel for bare Python runtimes."""

        def __init__(self, **kwargs: Any) -> None:
            annotations = self._collect_annotations()
            known_fields = set(annotations.keys())
            for attr_name in dir(self.__class__):
                if not attr_name.startswith("_") and not callable(getattr(self.__class__, attr_name)):
                    known_fields.add(attr_name)

            # Reject unexpected fields if model_config forbids extra
            model_cfg = getattr(self.__class__, "model_config", {})
            if isinstance(model_cfg, dict) and model_cfg.get("extra") == "forbid":
                extra_keys = set(kwargs.keys()) - known_fields
                if extra_keys:
                    raise ValidationError(f"Extra fields not permitted: {sorted(extra_keys)}")

            for field_name in annotations:
                class_val = getattr(self.__class__, field_name, ...)
                if field_name in kwargs:
                    val = kwargs[field_name]
                elif isinstance(class_val, _FieldInfo):
                    if class_val.default_factory is not None:
                        val = class_val.default_factory()
                    elif class_val.default is not ...:
                        val = copy.deepcopy(class_val.default)
                    else:
                        raise ValidationError(f"Field '{field_name}' is required")
                elif class_val is not ...:
                    val = copy.deepcopy(class_val)
                else:
                    raise ValidationError(f"Field '{field_name}' is required")

                if isinstance(class_val, _FieldInfo) and val is not None:
                    if class_val.ge is not None and isinstance(val, (int, float)) and val < class_val.ge:
                        raise ValidationError(f"Field '{field_name}' must be >= {class_val.ge}")
                    if class_val.le is not None and isinstance(val, (int, float)) and val > class_val.le:
                        raise ValidationError(f"Field '{field_name}' must be <= {class_val.le}")
                    if class_val.min_length is not None and hasattr(val, "__len__") and len(val) < class_val.min_length:
                        raise ValidationError(f"Field '{field_name}' length must be >= {class_val.min_length}")
                    if class_val.max_length is not None and hasattr(val, "__len__") and len(val) > class_val.max_length:
                        raise ValidationError(f"Field '{field_name}' length must be <= {class_val.max_length}")

                setattr(self, field_name, val)

            for k, v in kwargs.items():
                if k not in annotations:
                    setattr(self, k, v)

        @classmethod
        def _collect_annotations(cls) -> Dict[str, Any]:
            merged: Dict[str, Any] = {}
            for base in reversed(cls.__mro__):
                if base is object or base is BaseModel:
                    continue
                ann = getattr(base, "__annotations__", {})
                merged.update(ann)
            return merged

        @classmethod
        def model_validate(cls, data: Any) -> Any:
            if isinstance(data, cls):
                return data
            if not isinstance(data, dict):
                raise ValidationError(f"Expected dict for {cls.__name__}, got {type(data).__name__}")
            return cls(**data)

        @classmethod
        def model_validate_json(cls, raw_json: str) -> Any:
            try:
                parsed = json.loads(raw_json)
            except Exception as exc:
                raise ValidationError(f"Invalid JSON: {exc}") from exc
            return cls.model_validate(parsed)

        def model_dump(self) -> Dict[str, Any]:
            result: Dict[str, Any] = {}
            annotations = self._collect_annotations()
            for key in annotations:
                val = getattr(self, key, None)
                result[key] = _serialize_value(val)
            return result

        def model_dump_json(self) -> str:
            return json.dumps(self.model_dump())


def _serialize_value(val: Any) -> Any:
    if hasattr(val, "model_dump"):
        return val.model_dump()
    if isinstance(val, list):
        return [_serialize_value(item) for item in val]
    if isinstance(val, dict):
        return {k: _serialize_value(v) for k, v in val.items()}
    return val


try:
    from fastapi import APIRouter, Depends, FastAPI, File, Form, Header, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect, status  # type: ignore
    from fastapi.responses import JSONResponse  # type: ignore
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

    class WebSocket:  # type: ignore
        async def accept(self) -> None: pass
        async def receive_text(self) -> str: return ""
        async def receive_bytes(self) -> bytes: return b""
        async def receive(self) -> Dict[str, Any]: return {}
        async def send_text(self, data: str) -> None: pass
        async def send_json(self, data: Any) -> None: pass
        async def close(self, code: int = 1000) -> None: pass

    class WebSocketDisconnect(Exception):  # type: ignore
        def __init__(self, code: int = 1000) -> None:
            self.code = code

    class status:  # type: ignore
        HTTP_200_OK = 200
        HTTP_201_CREATED = 201
        HTTP_204_NO_CONTENT = 204
        HTTP_400_BAD_REQUEST = 400
        HTTP_401_UNAUTHORIZED = 401
        HTTP_404_NOT_FOUND = 404
        HTTP_413_REQUEST_ENTITY_TOO_LARGE = 413
        HTTP_415_UNSUPPORTED_MEDIA_TYPE = 415
        HTTP_422_UNPROCESSABLE_ENTITY = 422
        HTTP_502_BAD_GATEWAY = 502
        HTTP_503_SERVICE_UNAVAILABLE = 503
        HTTP_504_GATEWAY_TIMEOUT = 504

    class HTTPException(Exception):  # type: ignore
        def __init__(self, status_code: int, detail: Any = None) -> None:
            super().__init__(str(detail))
            self.status_code = status_code
            self.detail = detail

    class JSONResponse:  # type: ignore
        def __init__(self, content: Any, status_code: int = 200) -> None:
            self.content = content
            self.status_code = status_code

    class UploadFile:  # type: ignore
        def __init__(
            self,
            filename: str = "audio.wav",
            content: bytes = b"",
            content_type: str = "audio/wav",
        ) -> None:
            self.filename = filename
            self._content = content
            self.content_type = content_type

        async def read(self) -> bytes:
            return self._content

    def Depends(dependency: Optional[Callable[..., Any]] = None) -> Any:  # type: ignore
        return ("__depends__", dependency)

    def File(default: Any = ..., **kwargs: Any) -> Any:  # type: ignore
        return default

    def Form(default: Any = ..., **kwargs: Any) -> Any:  # type: ignore
        return default

    def Header(default: Any = None, **kwargs: Any) -> Any:  # type: ignore
        return default

    def Query(default: Any = None, **kwargs: Any) -> Any:  # type: ignore
        return default

    class _RouteEntry:
        def __init__(
            self,
            method: str,
            path: str,
            endpoint: Callable[..., Any],
            status_code: int = 200,
            response_model: Any = None,
        ) -> None:
            self.method = method.upper()
            self.path = path
            self.endpoint = endpoint
            self.status_code = status_code
            self.response_model = response_model
            param_names = re.findall(r"\{([a-zA-Z0-9_]+)\}", path)
            pattern = re.sub(r"\{[a-zA-Z0-9_]+\}", r"([^/]+)", path)
            self.regex = re.compile(f"^{pattern}$")
            self.param_names = param_names

    class APIRouter:  # type: ignore
        def __init__(self, prefix: str = "", tags: Optional[List[str]] = None) -> None:
            self.prefix = prefix.rstrip("/")
            self.tags = tags or []
            self.routes: List[_RouteEntry] = []

        def _add(self, method: str, path: str, status_code: int = 200, response_model: Any = None) -> Callable[..., Any]:
            full_path = f"{self.prefix}{path}" if path.startswith("/") else f"{self.prefix}/{path}"
            def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
                self.routes.append(_RouteEntry(method, full_path, fn, status_code=status_code, response_model=response_model))
                return fn
            return decorator

        def get(self, path: str, status_code: int = 200, response_model: Any = None, **kwargs: Any) -> Callable[..., Any]:
            return self._add("GET", path, status_code=status_code, response_model=response_model)

        def post(self, path: str, status_code: int = 200, response_model: Any = None, **kwargs: Any) -> Callable[..., Any]:
            return self._add("POST", path, status_code=status_code, response_model=response_model)

        def delete(self, path: str, status_code: int = 200, response_model: Any = None, **kwargs: Any) -> Callable[..., Any]:
            return self._add("DELETE", path, status_code=status_code, response_model=response_model)

        def websocket(self, path: str, **kwargs: Any) -> Callable[..., Any]:
            def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
                return fn
            return decorator

    class FastAPI(APIRouter):  # type: ignore
        def __init__(self, title: str = "FastAPI", version: str = "1.0.0", description: str = "", **kwargs: Any) -> None:
            super().__init__(prefix="")
            self.title = title
            self.version = version
            self.description = description
            self.dependency_overrides: Dict[Callable[..., Any], Callable[..., Any]] = {}

        def include_router(self, router: APIRouter, prefix: str = "", tags: Optional[List[str]] = None) -> None:
            clean_prefix = prefix.rstrip("/")
            for route in router.routes:
                combined = f"{clean_prefix}{route.path}" if clean_prefix else route.path
                self.routes.append(
                    _RouteEntry(
                        route.method,
                        combined,
                        route.endpoint,
                        status_code=route.status_code,
                        response_model=route.response_model,
                    )
                )


class LocalTestResponse:
    """HTTP response object returned by LocalTestClient."""

    def __init__(self, status_code: int, body: Any) -> None:
        self.status_code = status_code
        self._body = body
        self.text = json.dumps(body) if body is not None else ""

    def json(self) -> Any:
        return self._body


class LocalTestClient:
    """
    TestClient that uses `fastapi.testclient.TestClient` when FastAPI is installed,
    or dispatches directly to the registered FastAPI routes in bare Python environments.
    """

    def __init__(self, app: FastAPI) -> None:
        self.app = app
        self._native_client = None
        if FASTAPI_AVAILABLE:
            try:
                from fastapi.testclient import TestClient as NativeTestClient  # type: ignore
                self._native_client = NativeTestClient(app)
            except Exception:
                self._native_client = None

    def get(self, path: str, headers: Optional[Dict[str, str]] = None) -> Any:
        if self._native_client is not None:
            return self._native_client.get(path, headers=headers)
        return self._dispatch("GET", path, headers=headers)

    def delete(self, path: str, headers: Optional[Dict[str, str]] = None) -> Any:
        if self._native_client is not None:
            return self._native_client.delete(path, headers=headers)
        return self._dispatch("DELETE", path, headers=headers)

    def post(
        self,
        path: str,
        json: Any = None,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Tuple[str, bytes, str]]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        if self._native_client is not None:
            return self._native_client.post(path, json=json, data=data, files=files, headers=headers)
        return self._dispatch("POST", path, json_body=json, form_data=data, files=files, headers=headers)

    def _dispatch(
        self,
        method: str,
        raw_path: str,
        json_body: Any = None,
        form_data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Tuple[str, bytes, str]]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> LocalTestResponse:
        path = raw_path.split("?")[0]
        for route in self.app.routes:
            if route.method != method.upper():
                continue
            match = route.regex.match(path)
            if not match:
                continue

            path_params = dict(zip(route.param_names, match.groups()))
            try:
                kwargs = self._build_kwargs(route.endpoint, path_params, json_body, form_data, files, headers)
                if inspect.iscoroutinefunction(route.endpoint):
                    res = asyncio.run(route.endpoint(**kwargs))
                else:
                    res = route.endpoint(**kwargs)

                if isinstance(res, JSONResponse):
                    return LocalTestResponse(res.status_code, _serialize_value(res.content))
                return LocalTestResponse(route.status_code, _serialize_value(res))
            except HTTPException as http_exc:
                return LocalTestResponse(http_exc.status_code, {"detail": http_exc.detail})
            except ValidationError as val_exc:
                return LocalTestResponse(422, {"detail": str(val_exc)})

        return LocalTestResponse(404, {"detail": "Not Found"})

    def _build_kwargs(
        self,
        endpoint: Callable[..., Any],
        path_params: Dict[str, str],
        json_body: Any,
        form_data: Optional[Dict[str, Any]],
        files: Optional[Dict[str, Tuple[str, bytes, str]]],
        headers: Optional[Dict[str, str]],
    ) -> Dict[str, Any]:
        sig = inspect.signature(endpoint)
        type_hints = getattr(endpoint, "__annotations__", {})
        kwargs: Dict[str, Any] = {}

        for name, param in sig.parameters.items():
            default = param.default
            if isinstance(default, tuple) and len(default) == 2 and default[0] == "__depends__":
                dep_fn = default[1]
                override = self.app.dependency_overrides.get(dep_fn, dep_fn)
                kwargs[name] = override()
                continue

            if name in path_params:
                kwargs[name] = path_params[name]
                continue

            if files and name in files:
                fname, fbytes, ftype = files[name]
                kwargs[name] = UploadFile(filename=fname, content=fbytes, content_type=ftype)
                continue

            if form_data and name in form_data:
                kwargs[name] = form_data[name]
                continue

            # Resolve Pydantic request body parameter
            hint = type_hints.get(name)
            if isinstance(hint, str):
                # Resolve from endpoint globals
                hint = endpoint.__globals__.get(hint)

            if hint is not None and isinstance(hint, type) and issubclass(hint, BaseModel):
                if json_body is None:
                    raise ValidationError(f"Missing request body for {name}")
                kwargs[name] = hint.model_validate(json_body)
                continue

            if json_body is not None and isinstance(json_body, dict) and name in json_body:
                kwargs[name] = json_body[name]
                continue

            if default is not inspect.Parameter.empty:
                kwargs[name] = default

        return kwargs
